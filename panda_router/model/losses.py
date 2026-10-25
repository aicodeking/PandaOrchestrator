"""Per-head losses, distillation, minimal-pair ranking loss and initial-value loss normalisation."""

import torch
import torch.nn.functional as F

from ..taxonomy import CHECKLIST_IDS, FLAGS, SKILL_AXES
from .corn import corn_level_probs, corn_loss, expected_level

QUANTILES = (0.1, 0.5, 0.9)


def pinball(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """pred (B,3) quantiles, target (B,) -> mean pinball loss."""
    taus = torch.tensor(QUANTILES, device=pred.device, dtype=pred.dtype)
    diff = target.unsqueeze(-1) - pred
    return torch.maximum(taus * diff, (taus - 1) * diff).mean()


def head_losses(out: dict, y: dict) -> dict:
    return {
        "category": -(y["category"] * F.log_softmax(out["category"], -1)).sum(-1).mean(),
        "difficulty": corn_loss(out["difficulty"], y["difficulty"]),
        "skills": corn_loss(out["skills"], y["skills"]),
        "flags": F.binary_cross_entropy_with_logits(out["flags"], y["flags"]),
        "checklist": F.binary_cross_entropy_with_logits(out["checklist"], y["checklist"]),
        "out_tokens": pinball(out["out_tokens"], y["out_tokens"]),
    }


def _kl_cat(p_t, p_s):
    return (p_t * (p_t.clamp_min(1e-8).log() - p_s.clamp_min(1e-8).log())).sum(-1).mean()


def _kl_bern(p_t, p_s):
    p_t, p_s = p_t.clamp(1e-6, 1 - 1e-6), p_s.clamp(1e-6, 1 - 1e-6)
    return (p_t * (p_t / p_s).log() + (1 - p_t) * ((1 - p_t) / (1 - p_s)).log()).mean()


def distill_losses(out: dict, teacher: dict, T: float = 3.0) -> dict:
    """KL per head at temperature T (scaled by T^2); quantile head regresses teacher quantiles."""
    t2 = T * T
    return {
        "category": t2 * _kl_cat(F.softmax(teacher["category"] / T, -1), F.softmax(out["category"] / T, -1)),
        "difficulty": t2 * _kl_cat(corn_level_probs(teacher["difficulty"] / T), corn_level_probs(out["difficulty"] / T)),
        "skills": t2 * _kl_cat(corn_level_probs(teacher["skills"] / T), corn_level_probs(out["skills"] / T)),
        "flags": t2 * _kl_bern(torch.sigmoid(teacher["flags"] / T), torch.sigmoid(out["flags"] / T)),
        "checklist": t2 * _kl_bern(torch.sigmoid(teacher["checklist"] / T), torch.sigmoid(out["checklist"] / T)),
        "out_tokens": F.smooth_l1_loss(out["out_tokens"], teacher["out_tokens"]),
    }


def parse_delta(key: str, value) -> int:
    """expected_delta value -> sign of (edited - original): +1, -1, or 0 (unchanged)."""
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("+", "up", "increase", "higher", "more"):
            return 1
        if v in ("-", "down", "decrease", "lower", "less"):
            return -1
        if v in ("=", "0", "same", "none"):
            return 0
        try:
            value = float(v)
        except ValueError:
            return 0
    if isinstance(value, bool):
        value = float(value)
    head = key.split(".", 1)[0]
    if head in ("flags", "checklist"):
        return 1 if value >= 0.5 else -1  # target state of the flag after the edit
    return int(value > 0) - int(value < 0)


def pair_quantity(out: dict, key: str):
    """Scalar per example for a delta key, or None if unsupported."""
    head, _, name = key.partition(".")
    if head == "difficulty":
        return expected_level(corn_level_probs(out["difficulty"]), 1.0), 1.0
    if head == "skills" and name in SKILL_AXES:
        return expected_level(corn_level_probs(out["skills"][:, SKILL_AXES.index(name)])), 1.0
    if head == "flags" and name in FLAGS:
        return torch.sigmoid(out["flags"][:, FLAGS.index(name)]), 0.2
    if head == "checklist" and name in CHECKLIST_IDS:
        return torch.sigmoid(out["checklist"][:, CHECKLIST_IDS.index(name)]), 0.2
    return None


def pair_loss(out: dict, pairs: list, margin_scale: float = 0.5) -> torch.Tensor | None:
    """pairs: [(i_edited, j_original, {key: value})]. Margin ranking on expected difficulty/skills and flag probs."""
    terms = []
    cache = {}
    for i, j, deltas in pairs:
        for key, value in deltas.items():
            if key not in cache:
                cache[key] = pair_quantity(out, key)
            if cache[key] is None:
                continue
            q, unit = cache[key]
            sign = parse_delta(key, value)
            d = q[i] - q[j]
            m = margin_scale * unit
            terms.append(torch.relu(m - sign * d) if sign else torch.relu(d.abs() - m))
    return torch.stack(terms).mean() if terms else None


class LossNormalizer:
    """Divides each named loss by its first observed (non-zero) value."""

    def __init__(self):
        self.init: dict[str, float] = {}

    def __call__(self, name: str, value: torch.Tensor) -> torch.Tensor:
        if name not in self.init:
            v = float(value.detach())
            if v <= 1e-8:
                return value
            self.init[name] = v
        return value / self.init[name]

    def state_dict(self):
        return dict(self.init)
