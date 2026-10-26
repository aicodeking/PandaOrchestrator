"""Differentiable matcher (CONTRACTS.md "Matcher") + decision-focused regret loss.

P(success) for card i with per-axis theta_k ± se_k and discrimination a_i:
  w_k = E[skill_k] / sum E[skill]   (one-hot on `reasoning` if every E[skill] ~ 0)
  theta_eff = sum_k w_k theta_k ;  pen = lam * sum_k w_k max(0, E[skill_k] - theta_k)
  P_i = E_{b ~ difficulty, theta ~ N(theta, se)} sigmoid(a_i (theta_eff - pen - b))
Mirrors panda_router.matcher.core: the effective ability z = theta_eff - pen is approximated as
Normal(mu, sd) with mu/sd moment-matched per axis for the hinge max(0, E[skill_k] - theta_k) with
theta_k ~ N(theta_k, se_k) (see core.py docstring); the expectation over z uses fixed 20-node
Gauss-Hermite quadrature and the expectation over b is exact (levels 1..10).

Utility (PLAN.md §4, max_utility mode, no quality term):
  U_i = w_q P_i - w_c cost_i / max_j cost_j,  cost_i = (in_tok * price_in_i + 10**p50 * price_out_i) / 1e6
Regret = U_true[argmax U_true] - sum_i softmax(U_pred / tau)_i U_true_i, U_true from the label profile.
"""

import math
from dataclasses import dataclass

import numpy as np
import torch

from ..taxonomy import N_DIFFICULTY, N_SKILL_LEVELS, SKILL_AXES

LAMBDA = 0.5
N_QUAD = 20
REASONING = SKILL_AXES.index("reasoning")


def quadrature(n: int = N_QUAD) -> tuple[np.ndarray, np.ndarray]:
    """Standard-normal nodes and probability weights (physicists' Hermite, rescaled)."""
    x, w = np.polynomial.hermite.hermgauss(n)
    return np.sqrt(2.0) * x, w / np.sqrt(np.pi)


def skill_weights(skill_probs: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """(B,A,11) -> (w (B,A), E[skill] (B,A))."""
    levels = torch.arange(N_SKILL_LEVELS, device=skill_probs.device, dtype=skill_probs.dtype)
    e = (skill_probs * levels).sum(-1)
    tot = e.sum(-1, keepdim=True)
    onehot = torch.zeros_like(e)
    onehot[:, REASONING] = 1.0
    w = torch.where(tot > 1e-6, e / tot.clamp_min(1e-6), onehot)
    return w, e


def p_success(diff_probs, skill_probs, theta, se, a, lam: float = LAMBDA, n_quad: int = N_QUAD):
    """diff_probs (B,10), skill_probs (B,A,11), theta/se (B,M,A), a (B,M) -> P (B,M)."""
    w, e = skill_weights(skill_probs)
    zq, wq = quadrature(n_quad)
    zq = torch.as_tensor(zq, device=theta.device, dtype=theta.dtype)
    wq = torch.as_tensor(wq, device=theta.device, dtype=theta.dtype)
    wv = w.unsqueeze(1)  # (B,1,A)
    m = e.unsqueeze(1) - theta  # (B,M,A)
    sa = se.clamp_min(1e-9)
    t = m / sa
    cdf = torch.special.ndtr(t)
    pdf = torch.exp(-0.5 * t * t) / math.sqrt(2.0 * math.pi)
    eh = m * cdf + sa * pdf
    var_h = ((m * m + sa * sa) * cdf + m * sa * pdf - eh * eh).clamp_min(0.0)
    mu = (wv * (theta - lam * eh)).sum(-1)  # (B,M)
    sd = ((sa * sa + lam * lam * var_h + 2.0 * lam * sa * sa * cdf) * wv * wv).sum(-1).clamp_min(1e-12).sqrt()
    z = mu.unsqueeze(-1) + sd.unsqueeze(-1) * zq  # (B,M,G)
    b = torch.arange(1, N_DIFFICULTY + 1, device=theta.device, dtype=theta.dtype)
    sig = torch.sigmoid(a.view(*a.shape, 1, 1) * (z.unsqueeze(-1) - b))  # (B,M,G,10)
    p_level = (sig * wq.view(1, 1, -1, 1)).sum(2)  # (B,M,10)
    return (p_level * diff_probs.unsqueeze(1)).sum(-1)


@dataclass
class CardPool:
    theta: torch.Tensor  # (B,M,A) on 0..10
    se: torch.Tensor  # (B,M,A)
    a: torch.Tensor  # (B,M)
    price_in: torch.Tensor  # (B,M) USD per Mtok
    price_out: torch.Tensor  # (B,M)
    w_q: torch.Tensor  # (B,1)
    w_c: torch.Tensor  # (B,1)


def sample_pools(batch: int, n_cards: int = 6, generator: torch.Generator | None = None, device="cpu") -> CardPool:
    """Random synthetic pools: stronger cards cost more (log-linear), with per-axis spikes and noise."""
    g = generator
    a_axes = len(SKILL_AXES)
    r = lambda *s: torch.rand(*s, generator=g)  # noqa: E731
    base = 1.5 + 8.0 * r(batch, n_cards, 1)
    theta = (base + 1.5 * torch.randn(batch, n_cards, a_axes, generator=g)).clamp(0.0, 10.0)
    se = 0.2 + 1.3 * r(batch, n_cards, a_axes)
    a = 0.8 + 1.2 * r(batch, n_cards)
    log_price = -1.0 + 0.25 * base.squeeze(-1) + 0.4 * torch.randn(batch, n_cards, generator=g)
    price_in = 10 ** log_price
    price_out = price_in * (3.0 + 3.0 * r(batch, n_cards))
    w_q = torch.ones(batch, 1)
    w_c = 0.05 + 0.5 * r(batch, 1)
    t = lambda x: x.to(device)  # noqa: E731
    return CardPool(t(theta), t(se), t(a), t(price_in), t(price_out), t(w_q), t(w_c))


def utility(p, out_tokens_log10_p50, in_tokens, pool: CardPool):
    """p (B,M), p50 (B,), in_tokens (B,) -> U (B,M)."""
    out_tok = 10 ** out_tokens_log10_p50.clamp(0.0, 6.0)
    cost = (in_tokens.unsqueeze(-1) * pool.price_in + out_tok.unsqueeze(-1) * pool.price_out) / 1e6
    norm = cost / cost.max(-1, keepdim=True).values.clamp_min(1e-12)
    return pool.w_q * p - pool.w_c * norm


MIN_P = 0.75  # matcher default min_p_success (panda_router.matcher.policy.DEFAULTS)


def cheapest_score(p, out_tokens_log10_p50, in_tokens, pool: CardPool, min_p: float = MIN_P, s: float = 0.03):
    """Smooth stand-in for cheapest_above_threshold: cards with P >= min_p score 1 - normalised cost-to-success
    (cost / P, as in the policy), the rest score P - 1 < 0, so the relaxed fallback (max P) is kept when no card
    clears the threshold. The feasibility gate is sigmoid((P - min_p) / s)."""
    out_tok = 10 ** out_tokens_log10_p50.clamp(0.0, 6.0)
    cost = (in_tokens.unsqueeze(-1) * pool.price_in + out_tok.unsqueeze(-1) * pool.price_out) / 1e6
    cts = cost / p.clamp_min(1e-3)
    norm = cts / cts.max(-1, keepdim=True).values.clamp_min(1e-12)
    gate = torch.sigmoid((p - min_p) / s)
    return gate * (1.0 - norm) + (1.0 - gate) * (p - 1.0)


def regret_loss(pred: dict, label: dict, in_tokens: torch.Tensor, pool: CardPool, tau: float = 0.05,
                reduce: bool = True, mode: str = "max_utility", w: torch.Tensor | None = None):
    """pred/label: dicts with difficulty (B,10), skills (B,A,11) probs and out_p50 (B,) log10 values.
    mode: "max_utility" (utility) or "cheapest" (cheapest_score). `w` (B,) weights rows (0 masks)."""
    score = {"max_utility": utility, "cheapest": cheapest_score}[mode]
    u_pred = score(p_success(pred["difficulty"], pred["skills"], pool.theta, pool.se, pool.a),
                   pred["out_p50"], in_tokens, pool)
    with torch.no_grad():
        u_true = score(p_success(label["difficulty"], label["skills"], pool.theta, pool.se, pool.a),
                       label["out_p50"], in_tokens, pool)
    soft = torch.softmax(u_pred / tau, dim=-1)
    regret = u_true.max(-1).values - (soft * u_true).sum(-1)
    if not reduce:
        return regret
    return regret.mean() if w is None else (regret * w).sum() / w.sum().clamp_min(1e-8)
