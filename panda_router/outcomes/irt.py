"""MAP IRT on binomial counts (persons = systems, items = tasks).

logit P(resolve | system s, task i) = a_i * (theta_s - b_i), with theta ~ N(0, 1) (fixes the scale),
b ~ N(0, PRIOR_B^2), log a ~ N(0, PRIOR_LOGA^2). `two_pl=False` fixes a_i = 1 and theta ~ N(0, PRIOR_THETA_1PL^2)
(the scale is then fixed by a = 1, like eval/anchors.fit_1pl).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

PRIOR_B, PRIOR_LOGA, PRIOR_THETA_1PL = 3.0, 0.5, 3.0


@dataclass(frozen=True)
class IRTFit:
    theta: np.ndarray
    b: np.ndarray
    a: np.ndarray
    se_b: np.ndarray
    se_theta: np.ndarray
    two_pl: bool

    def prob(self, s: np.ndarray, i: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-self.a[i] * (self.theta[s] - self.b[i])))


def fit_irt(s: np.ndarray, i: np.ndarray, k: np.ndarray, n: np.ndarray, n_sys: int, n_items: int,
            two_pl: bool = True, maxiter: int = 5000) -> IRTFit:
    from scipy.optimize import minimize

    s, i = np.asarray(s), np.asarray(i)
    k, n = np.asarray(k, float), np.asarray(n, float)
    pt = 1.0 if two_pl else PRIOR_THETA_1PL

    def unpack(x):
        th, b = x[:n_sys], x[n_sys:n_sys + n_items]
        la = x[n_sys + n_items:] if two_pl else np.zeros(n_items)
        return th, b, la

    def f(x):
        th, b, la = unpack(x)
        a = np.exp(la)
        d = th[s] - b[i]
        eta = a[i] * d
        nll = -(k * eta - n * np.logaddexp(0.0, eta)).sum()
        nll += 0.5 * ((th / pt) ** 2).sum() + 0.5 * ((b / PRIOR_B) ** 2).sum()
        r = n / (1.0 + np.exp(-eta)) - k  # d nll / d eta
        g_th = np.bincount(s, weights=r * a[i], minlength=n_sys) + th / pt ** 2
        g_b = -np.bincount(i, weights=r * a[i], minlength=n_items) + b / PRIOR_B ** 2
        g = [g_th, g_b]
        if two_pl:
            nll += 0.5 * ((la / PRIOR_LOGA) ** 2).sum()
            g.append(np.bincount(i, weights=r * eta, minlength=n_items) + la / PRIOR_LOGA ** 2)
        return nll, np.concatenate(g)

    x0 = np.zeros(n_sys + n_items * (2 if two_pl else 1))
    res = minimize(f, x0, jac=True, method="L-BFGS-B", options={"maxiter": maxiter, "maxfun": maxiter * 2})
    th, b, la = unpack(res.x)
    a = np.exp(la)
    p = 1.0 / (1.0 + np.exp(-a[i] * (th[s] - b[i])))
    w = n * p * (1 - p) * a[i] ** 2  # diagonal Laplace approximation, other parameters held fixed
    se_b = 1.0 / np.sqrt(np.bincount(i, weights=w, minlength=n_items) + 1.0 / PRIOR_B ** 2)
    se_th = 1.0 / np.sqrt(np.bincount(s, weights=w, minlength=n_sys) + 1.0 / pt ** 2)
    return IRTFit(th, b, a, se_b, se_th, two_pl)


def heldout_metrics(s, i, k, n, n_sys, n_items, two_pl: bool, frac: float = 0.1, seed: int = 0) -> dict:
    """Mask a random `frac` of (system, task) cells, fit on the rest, score the masked trials."""
    from sklearn.metrics import roc_auc_score

    s, i, k, n = map(np.asarray, (s, i, k, n))
    test = np.random.default_rng(seed).random(len(s)) < frac
    fit = fit_irt(s[~test], i[~test], k[~test], n[~test], n_sys, n_items, two_pl=two_pl)
    p = np.clip(fit.prob(s[test], i[test]), 1e-6, 1 - 1e-6)
    kt, nt = k[test].astype(float), n[test].astype(float)
    logloss = -(kt * np.log(p) + (nt - kt) * np.log(1 - p)).sum() / nt.sum()
    # expand binomial cells into per-trial labels for AUC
    y = np.concatenate([np.ones(int(kt.sum())), np.zeros(int((nt - kt).sum()))])
    sc = np.concatenate([np.repeat(p, kt.astype(int)), np.repeat(p, (nt - kt).astype(int))])
    base = kt.sum() / nt.sum()
    base_ll = -(base * np.log(base) + (1 - base) * np.log(1 - base))
    return {"model": "2PL" if two_pl else "1PL", "heldout_cells": int(test.sum()), "heldout_trials": int(nt.sum()),
            "logloss": float(logloss), "auc": float(roc_auc_score(y, sc)), "base_rate_logloss": float(base_ll)}


def _map_location(c, a, k, n, g, n_groups, sign, prior_mu, prior_sd, iters=50):
    """Per-group MAP of u in logit P = a * sign * (u - c), prior u ~ N(prior_mu, prior_sd^2); Newton (concave)."""
    c, a, k, n = (np.asarray(x, float) for x in (c, a, k, n))
    mu = np.broadcast_to(np.asarray(prior_mu, float), (n_groups,))
    u = mu.copy()
    for _ in range(iters):
        p = 1.0 / (1.0 + np.exp(-a * sign * (u[g] - c)))
        grad = np.bincount(g, weights=a * sign * (k - n * p), minlength=n_groups) - (u - mu) / prior_sd ** 2
        info = np.bincount(g, weights=n * p * (1 - p) * a ** 2, minlength=n_groups) + 1.0 / prior_sd ** 2
        step = np.clip(grad / info, -2.0, 2.0)
        u = u + step
        if np.abs(step).max() < 1e-8:
            break
    return u, 1.0 / np.sqrt(info)


def fit_b_given_theta(theta, a, k, n, item, n_items, prior_sd: float = PRIOR_B):
    """Item difficulties with person abilities (per cell: theta[s], a) held fixed. Returns (b, se_b)."""
    return _map_location(theta, a, k, n, np.asarray(item), n_items, -1.0, 0.0, prior_sd)


def fit_theta_given_b(b, a, k, n, person, n_persons, prior_mu=0.0, prior_sd: float = 1.0):
    """Person abilities with item parameters (per cell: b[i], a[i]) held fixed. Returns (theta, se_theta)."""
    return _map_location(b, a, k, n, np.asarray(person), n_persons, 1.0, prior_mu, prior_sd)
