"""P(success): compensatory MIRT + bottleneck penalty, integrated over difficulty and theta uncertainty.

For task axis weights w (w_k = E[skill_k] / sum E[skill]) and model i with per-axis theta_k ~ N(theta_k, se_k):

    z_i   = sum_k w_k theta_k - lambda * sum_k w_k max(0, E[skill_k] - theta_k)     (lambda = 0.5)
    P_i   = E_{b ~ difficulty, z ~ N(mu_i, sd_i)} sigmoid(a_i (z - b))

z is a linear-plus-hinge function of theta. We approximate it as Normal, moment-matched per axis:
with h_k = max(0, g_k - theta_k) and m = g_k - theta_k-mean, s = se_k, E[h] = m Phi(m/s) + s phi(m/s),
E[h^2] = (m^2 + s^2) Phi(m/s) + m s phi(m/s), and Cov(theta_k, h_k) = -s^2 Phi(m/s) (Stein). Axes are
independent, so mu_i and sd_i are sums of the per-axis means/variances of w_k (theta_k - lambda h_k).
We then integrate exactly over the 10 difficulty levels and with 20-node Gauss-Hermite quadrature over z.
Fully deterministic.
"""

from __future__ import annotations

import numpy as np
from scipy.special import ndtr

from ..taxonomy import SKILL_AXES

LAMBDA = 0.5
GH_NODES = 20
LEVELS = np.arange(1, 11, dtype=float)
_GH_X, _GH_W = np.polynomial.hermite.hermgauss(GH_NODES)
_GH_Z = np.sqrt(2.0) * _GH_X
_GH_P = _GH_W / np.sqrt(np.pi)
_REASONING = SKILL_AXES.index("reasoning")


def expected_skills(skills: dict[str, list[float]]) -> np.ndarray:
    out = np.zeros(len(SKILL_AXES))
    for k, axis in enumerate(SKILL_AXES):
        if dist := skills.get(axis):
            out[k] = float(np.dot(np.arange(len(dist)), dist))
    return out


def axis_weights(exp_skill: np.ndarray) -> np.ndarray:
    total = float(exp_skill.sum())
    if total < 1e-6:
        w = np.zeros(len(SKILL_AXES))
        w[_REASONING] = 1.0
        return w
    return exp_skill / total


def ability_moments(w: np.ndarray, exp_skill: np.ndarray, theta: np.ndarray, se: np.ndarray,
                    lam: float = LAMBDA) -> tuple[np.ndarray, np.ndarray]:
    """Mean and sd of the effective ability z for each model (rows of theta/se)."""
    m = exp_skill[None, :] - theta
    s = np.maximum(se, 1e-9)
    t = m / s
    cdf, pdf = ndtr(t), np.exp(-0.5 * t * t) / np.sqrt(2.0 * np.pi)
    eh = m * cdf + s * pdf
    var_h = np.maximum((m * m + s * s) * cdf + m * s * pdf - eh * eh, 0.0)
    mu = ((theta - lam * eh) * w).sum(axis=1)
    var = ((s * s + lam * lam * var_h + 2.0 * lam * s * s * cdf) * w * w).sum(axis=1)
    return mu, np.sqrt(var)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 0.5 * (1.0 + np.tanh(0.5 * x))


def p_by_level(mu: np.ndarray, sd: np.ndarray, a: np.ndarray) -> np.ndarray:
    """(N, 10): P(success | b = level) integrated over z ~ N(mu, sd)."""
    z = mu[:, None] + sd[:, None] * _GH_Z[None, :]  # (N, G)
    logits = a[:, None, None] * (z[:, :, None] - LEVELS[None, None, :])  # (N, G, L)
    return np.einsum("g,ngl->nl", _GH_P, _sigmoid(logits))


def p_success(mu: np.ndarray, sd: np.ndarray, a: np.ndarray, difficulty: np.ndarray) -> np.ndarray:
    return p_by_level(mu, sd, a) @ difficulty


def success_probabilities(skills: dict[str, list[float]], difficulty, theta: np.ndarray, se: np.ndarray,
                          a: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convenience: returns (P, mu, sd) for a profile's skills/difficulty against card arrays."""
    exp = expected_skills(skills)
    w = axis_weights(exp)
    mu, sd = ability_moments(w, exp, np.atleast_2d(theta), np.atleast_2d(se))
    d = np.asarray(difficulty, dtype=float)
    return p_success(mu, sd, np.atleast_1d(np.asarray(a, dtype=float)), d / d.sum()), mu, sd


def difficulty_posterior_after_failure(prior: np.ndarray, p_level_failed: np.ndarray) -> np.ndarray:
    """Bayes: post(b) ∝ prior(b) * P(fail | b) for the model that failed."""
    post = np.asarray(prior, dtype=float) * (1.0 - p_level_failed)
    s = post.sum()
    return post / s if s > 1e-12 else np.asarray(prior, dtype=float)
