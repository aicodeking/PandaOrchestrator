"""Outcome anchors (PLAN.md 12.4 #1): empirical instance difficulty from published per-instance
agent outcomes, via a 1PL (Rasch) IRT model with binomial counts.

Sources (both CC-BY-4.0, published by Nebius, the SWE-rebench authors):
- nebius/SWE-rebench-openhands-trajectories: Qwen3-Coder-480B-A35B-Instruct + OpenHands v0.54,
  ~10 runs per SWE-rebench instance, column `resolved`.
- nebius/SWE-agent-trajectories: SWE-agent with Llama-3.1-8B/70B/405B-based policies on
  nebius/SWE-bench-extra (instance ids shared with SWE-rebench), column `target`.

Model: logit P(resolve | model m, instance i) = theta_m - b_i, MAP with Gaussian priors
(b ~ N(0, 2^2), theta ~ N(0, 3^2)), fitted on every instance with outcomes. A 2PL is not
identifiable with this few distinct models (<= 4), so it is not fitted.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
RAW = ROOT / "data" / "gold" / "raw"
PRIOR_B, PRIOR_THETA = 2.0, 3.0


def load_outcomes() -> "object":
    """DataFrame [instance_id, model, k, n] of binomial counts from the downloaded outcome columns."""
    import pandas as pd
    import pyarrow.parquet as pq

    frames = []
    p = RAW / "openhands-traj" / "outcomes.parquet"
    if p.exists():
        df = pq.read_table(p, columns=["instance_id", "resolved"]).to_pandas()
        df["model"] = "qwen3-coder-480b@openhands"
        df["y"] = df["resolved"].astype(float)
        frames.append(df[["instance_id", "model", "y"]])
    p = RAW / "swe-agent-traj" / "outcomes.parquet"
    if p.exists():
        df = pq.read_table(p, columns=["instance_id", "model_name", "target"]).to_pandas()
        df["model"] = df["model_name"] + "@swe-agent"
        df["y"] = df["target"].astype(float)
        frames.append(df[["instance_id", "model", "y"]])
    if not frames:
        raise FileNotFoundError("no outcome parquet files under data/gold/raw/")
    df = pd.concat(frames)
    return df.groupby(["instance_id", "model"]).y.agg(k="sum", n="count").reset_index()


def fit_1pl(inst_idx: np.ndarray, model_idx: np.ndarray, k: np.ndarray, n: np.ndarray, n_inst: int, n_models: int,
            prior_b: float = PRIOR_B, prior_theta: float = PRIOR_THETA) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """MAP 1PL with binomial counts. Returns (b, theta, se_b) with se_b from the diagonal Laplace approx."""
    from scipy.optimize import minimize

    k, n = np.asarray(k, float), np.asarray(n, float)

    def f(x):
        th, b = x[:n_models], x[n_models:]
        eta = th[model_idx] - b[inst_idx]
        p = 1.0 / (1.0 + np.exp(-eta))
        nll = -(k * eta - n * np.logaddexp(0.0, eta)).sum()
        nll += 0.5 * (b ** 2).sum() / prior_b ** 2 + 0.5 * (th ** 2).sum() / prior_theta ** 2
        r = n * p - k  # d nll / d eta
        g_th = np.bincount(model_idx, weights=r, minlength=n_models) + th / prior_theta ** 2
        g_b = -np.bincount(inst_idx, weights=r, minlength=n_inst) + b / prior_b ** 2
        return nll, np.concatenate([g_th, g_b])

    res = minimize(f, np.zeros(n_models + n_inst), jac=True, method="L-BFGS-B", options={"maxiter": 2000})
    th, b = res.x[:n_models], res.x[n_models:]
    p = 1.0 / (1.0 + np.exp(-(th[model_idx] - b[inst_idx])))
    info = np.bincount(inst_idx, weights=n * p * (1 - p), minlength=n_inst) + 1.0 / prior_b ** 2
    return b, th, 1.0 / np.sqrt(info)


def to_1_10(b: np.ndarray, ref: np.ndarray) -> np.ndarray:
    """Monotone linear rescale of b onto 1..10 using the 2nd-98th percentile of `ref` (all fitted instances)."""
    lo, hi = np.percentile(ref, [2, 98])
    return np.clip(1.0 + 9.0 * (b - lo) / max(hi - lo, 1e-6), 1.0, 10.0)


def fit_anchors() -> tuple[dict[str, dict], dict]:
    """Fit on every instance with outcomes; return per-instance anchors and model abilities."""
    df = load_outcomes()
    insts = sorted(df.instance_id.unique())
    models = sorted(df.model.unique())
    ii = {x: i for i, x in enumerate(insts)}
    mi = {x: i for i, x in enumerate(models)}
    inst_idx = df.instance_id.map(ii).to_numpy()
    model_idx = df.model.map(mi).to_numpy()
    b, th, se = fit_1pl(inst_idx, model_idx, df.k.to_numpy(), df.n.to_numpy(), len(insts), len(models))
    d110 = to_1_10(b, b)
    per = {}
    for row in df.itertuples():
        per.setdefault(row.instance_id, {})[row.model] = {"k": int(row.k), "n": int(row.n)}
    anchors = {x: {"irt_b": float(b[i]), "irt_b_se": float(se[i]), "difficulty_1_10": float(d110[i]),
                   "n_models": len(per[x]), "outcomes": per[x]} for x, i in ii.items()}
    fit = {"models": {m: {"theta": float(th[j]), "n_instances": int((model_idx == j).sum()),
                          "mean_success": float(df.k[model_idx == j].sum() / df.n[model_idx == j].sum())}
                      for m, j in mi.items()},
           "n_instances": len(insts), "n_cells": len(df), "n_trials": int(df.n.sum()),
           "prior_b_sd": PRIOR_B, "prior_theta_sd": PRIOR_THETA,
           "scale_1_10": "linear map of b, 2nd..98th percentile over all fitted instances -> 1..10, clipped"}
    return anchors, fit
