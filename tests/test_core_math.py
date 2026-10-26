"""Accuracy, monotonicity and speed of the analytic P(success) in matcher.core versus Monte Carlo."""

import time

import numpy as np

from panda_router.matcher.core import LEVELS, ability_moments, axis_weights, p_success
from panda_router.taxonomy import SKILL_AXES

A = len(SKILL_AXES)


def mc_p(w, e, theta, se, a, diff, lam=0.5, n=100_000, seed=0):
    """P over theta ~ N(theta, se) (per axis, independent) and b ~ diff, by plain Monte Carlo."""
    rng = np.random.default_rng(seed)
    th = theta[None, :] + se[None, :] * rng.standard_normal((n, A))
    z = th @ w - lam * (np.maximum(e[None, :] - th, 0.0) @ w)
    sig = 1.0 / (1.0 + np.exp(-a * (z[:, None] - LEVELS[None, :])))
    return float((sig.mean(0) * diff).sum())


def _cases(n=60, seed=3):
    """Hard grid: theta near the task's skill levels (hinge active), wide se."""
    rng = np.random.default_rng(seed)
    for _ in range(n):
        e = rng.uniform(0, 9, A) * (rng.random(A) < 0.6)
        e[0] = rng.uniform(2, 9)
        theta = np.clip(e + rng.normal(0, 1.5, A), 0, 10)
        yield e, rng.dirichlet(np.ones(10)), theta, rng.uniform(0.5, 2.5, A), rng.uniform(0.8, 2.0)


def _analytic(e, diff, theta, se, a):
    w = axis_weights(e)
    mu, sd = ability_moments(w, e, theta[None], se[None])
    return float(p_success(mu, sd, np.array([a]), diff)[0])


def test_matches_monte_carlo():
    errs = [abs(_analytic(e, d, t, s, a) - mc_p(axis_weights(e), e, t, s, a, d)) for e, d, t, s, a in _cases()]
    print(f"mean abs err {np.mean(errs):.5f} max {np.max(errs):.5f}")
    assert np.mean(errs) < 0.005 and np.max(errs) < 0.015


def test_monotonic_in_theta_and_difficulty():
    e = np.array([6.0 if k % 3 == 0 else 2.0 for k in range(A)])
    se, diff = np.full(A, 0.8), np.full(10, 0.1)
    ps = [_analytic(e, diff, np.full(A, t), se, 1.2) for t in np.linspace(0, 10, 21)]
    assert np.all(np.diff(ps) >= -1e-9)
    ps = [_analytic(e, np.eye(10)[b], np.full(A, 5.0), se, 1.2) for b in range(10)]
    assert np.all(np.diff(ps) <= 1e-9)


def test_speed_65_cards():
    rng = np.random.default_rng(0)
    e = rng.uniform(0, 8, A)
    w, theta, se = axis_weights(e), rng.uniform(0, 10, (65, A)), rng.uniform(0.2, 1.5, (65, A))
    a, diff = rng.uniform(0.8, 2.0, 65), rng.dirichlet(np.ones(10))
    ts = []
    for _ in range(50):
        t0 = time.perf_counter()
        mu, sd = ability_moments(w, e, theta, se)
        p_success(mu, sd, a, diff)
        ts.append(time.perf_counter() - t0)
    p50 = float(np.median(ts))
    print(f"65 cards p50 {p50 * 1e3:.3f} ms")
    assert p50 < 2e-3


def test_loss_normalizer_stable_for_sparse_losses():
    import torch

    from panda_router.model.losses import LossNormalizer

    n = LossNormalizer(warmup=10)
    vals = [0.0, 0.0, 5.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]  # sparse hinge: first batch is 0
    outs = [float(n("pair", torch.tensor(v))) for v in vals]
    assert all(np.isfinite(outs)) and max(outs) < 1e4
    assert abs(n.state_dict()["pair"] - 0.6) < 1e-9  # mean of warm-up window
    assert float(n("pair", torch.tensor(1.2))) == 1.2 / 0.6  # frozen after warm-up
