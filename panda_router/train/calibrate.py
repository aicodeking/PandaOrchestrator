"""Per-head temperature scaling fitted on validation (soft-target NLL), plus quantile-width scaling."""

import json
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from ..model.corn import corn_level_probs
from ..model.decode import decode_probs
from ..model.net import load_checkpoint, write_heads_json
from ..taxonomy import SKILL_AXES
from .data import ProfileDataset, stack_labels
from .metrics import compute_metrics


def _fit_t(nll_fn, init: float = 1.0) -> float:
    log_t = torch.tensor(np.log(init), dtype=torch.float64, requires_grad=True)
    opt = torch.optim.LBFGS([log_t], lr=0.1, max_iter=100, line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        loss = nll_fn(log_t.exp())
        loss.backward()
        return loss

    opt.step(closure)
    return float(log_t.detach().exp().clamp(0.05, 20.0))


def fit_temperatures(raw: dict, y: dict) -> dict:
    t = {k: torch.as_tensor(np.asarray(v), dtype=torch.float64) for k, v in raw.items()}
    yy = {k: torch.as_tensor(np.asarray(v), dtype=torch.float64) for k, v in y.items()}

    def soft_ce(p, q):
        return -(q * p.clamp_min(1e-9).log()).sum(-1).mean()

    def bce(logits, q):
        return F.binary_cross_entropy_with_logits(logits, q)

    temps = {
        "category": _fit_t(lambda T: soft_ce(F.softmax(t["category"] / T, -1), yy["category"])),
        "difficulty": _fit_t(lambda T: soft_ce(corn_level_probs(t["difficulty"] / T), yy["difficulty"])),
        "skills": [_fit_t(lambda T, k=k: soft_ce(corn_level_probs(t["skills"][:, k] / T), yy["skills"][:, k]))
                   for k in range(len(SKILL_AXES))],
        "flags": _fit_t(lambda T: bce(t["flags"] / T, yy["flags"])),
        "checklist": _fit_t(lambda T: bce(t["checklist"] / T, yy["checklist"])),
    }
    q, target = np.asarray(raw["out_tokens"]), np.asarray(y["out_tokens"])
    best_w, best_gap = 1.0, np.inf
    for w in np.exp(np.linspace(np.log(0.25), np.log(6.0), 60)):
        lo, hi = q[:, 1] - w * (q[:, 1] - q[:, 0]), q[:, 1] + w * (q[:, 2] - q[:, 1])
        gap = abs(((target >= lo) & (target <= hi)).mean() - 0.8)
        if gap < best_gap - 1e-9:
            best_w, best_gap = float(w), gap
    temps["out_tokens_width"] = best_w
    return temps


def calibrate_checkpoint(ckpt_dir, data_dir=None, val_ds=None, device="cpu", bf16=True) -> dict:
    from .trainer import predict

    model, tok, meta, _ = load_checkpoint(ckpt_dir, device)
    if val_ds is None:
        val_ds = ProfileDataset.from_file(Path(data_dir) / "val.jsonl", tok, meta.get("max_len", 512))
    raw = predict(model, val_ds, torch.device(device) if isinstance(device, str) else device, 64, bf16)
    y = stack_labels(val_ds.labels)
    temps = fit_temperatures(raw, y)
    before, after = compute_metrics(decode_probs(raw), y), compute_metrics(decode_probs(raw, temps), y)
    ece_keys = [k for k in after if k.endswith("_ece") or k == "out_tokens_coverage80"]
    report = {"temperatures": temps, "before": {k: before[k] for k in ece_keys}, "after": {k: after[k] for k in ece_keys}}
    write_heads_json(ckpt_dir, temps, meta, {"calibration": report})
    (Path(ckpt_dir) / "val_metrics.json").write_text(json.dumps(after, indent=2))
    return report
