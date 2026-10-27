"""CORN ordinal regression (Shi et al., 2021) with soft-label support.

K levels -> K-1 conditional binary tasks. Task j models P(y > j | y > j-1).
Level probs: P(y > j) = prod_{i<=j} sigmoid(f_i); p_k = P(y > k-1) - P(y > k).

Soft targets: for a target distribution q over levels, the survival S_j = P(y > j) = sum_{k>j} q_k.
Task j is trained on the conditioning mass S_{j-1} (S_{-1} = 1) with soft target S_j / S_{j-1}.
The weighted BCE is minimised exactly at f_j = logit(S_j / S_{j-1}), so the decoded level
distribution reproduces q (round trip).
"""

import torch
import torch.nn.functional as F

EPS = 1e-6


def corn_survival(logits: torch.Tensor) -> torch.Tensor:
    """(..., K-1) conditional logits -> (..., K-1) survival P(y > j)."""
    return torch.cumprod(torch.sigmoid(logits), dim=-1)


def corn_level_probs(logits: torch.Tensor) -> torch.Tensor:
    """(..., K-1) conditional logits -> (..., K) level distribution."""
    surv = corn_survival(logits)
    one = torch.ones_like(surv[..., :1])
    upper = torch.cat([one, surv], dim=-1)
    lower = torch.cat([surv, torch.zeros_like(one)], dim=-1)
    return (upper - lower).clamp_min(0.0)


def soft_to_corn_targets(q: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """(..., K) level distribution -> (targets, weights), each (..., K-1)."""
    q = q / q.sum(-1, keepdim=True).clamp_min(EPS)
    surv = (1.0 - torch.cumsum(q, dim=-1))[..., :-1].clamp(0.0, 1.0)
    prev = torch.cat([torch.ones_like(surv[..., :1]), surv[..., :-1]], dim=-1)
    targets = torch.where(prev > EPS, surv / prev.clamp_min(EPS), torch.zeros_like(surv)).clamp(0.0, 1.0)
    return targets, prev


def corn_targets_to_logits(targets: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    t = targets.clamp(eps, 1 - eps)
    return torch.log(t) - torch.log1p(-t)


def corn_loss(logits: torch.Tensor, q: torch.Tensor, reduce: bool = True, under_w: float = 1.0) -> torch.Tensor:
    """Soft-label CORN loss. logits (..., K-1), q (..., K). Returns mean (or per-row (...)) loss."""
    targets, weights = soft_to_corn_targets(q.float())
    bce = F.binary_cross_entropy_with_logits(logits.float(), targets, reduction="none")
    if under_w != 1.0:  # missing a 'level > k' target = under-prediction: weight it up
        bce = bce * (1 + (under_w - 1) * targets)
    per_row = (weights * bce).sum(-1) / logits.shape[-1]
    return per_row.mean() if reduce else per_row


def expected_level(probs: torch.Tensor, offset: float = 0.0) -> torch.Tensor:
    levels = torch.arange(probs.shape[-1], device=probs.device, dtype=probs.dtype) + offset
    return (probs * levels).sum(-1)
