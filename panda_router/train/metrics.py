"""Validation metrics per head. Inputs: decoded probs (decode_probs) and stacked label arrays."""

import warnings

import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics import cohen_kappa_score, f1_score, roc_auc_score


def ece(conf: np.ndarray, correct: np.ndarray, n_bins: int = 15) -> float:
    conf, correct = np.asarray(conf, float).ravel(), np.asarray(correct, float).ravel()
    bins = np.minimum((conf * n_bins).astype(int), n_bins - 1)
    total = 0.0
    for b in range(n_bins):
        m = bins == b
        if m.any():
            total += m.mean() * abs(conf[m].mean() - correct[m].mean())
    return float(total)


def binary_ece(p: np.ndarray, y: np.ndarray) -> float:
    """Reliability of P(y=1) against hard labels (y >= 0.5), over all columns."""
    return ece(p.ravel(), (y.ravel() >= 0.5).astype(float))


def _macro_auroc(p, y):
    yb = y >= 0.5
    scores = [roc_auc_score(yb[:, j], p[:, j]) for j in range(y.shape[1]) if 0 < yb[:, j].sum() < len(yb)]
    return float(np.mean(scores)) if scores else float("nan")


def compute_metrics(probs: dict, y: dict) -> dict:
    m = {}
    cat_true = y["category"].argmax(-1)
    order = np.argsort(-probs["category"], -1)
    m["category_acc"] = float((order[:, 0] == cat_true).mean())
    m["category_top2"] = float((order[:, :2] == cat_true[:, None]).any(-1).mean())
    m["category_ece"] = ece(probs["category"].max(-1), order[:, 0] == cat_true)

    lv = np.arange(1, 11)
    ed_p, ed_y = probs["difficulty"] @ lv, y["difficulty"] @ lv
    m["difficulty_mae"] = float(np.abs(ed_p - ed_y).mean())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rho = spearmanr(ed_p, ed_y).statistic
    m["difficulty_spearman"] = float(rho) if np.isfinite(rho) else 0.0
    dp, dy = probs["difficulty"].argmax(-1), y["difficulty"].argmax(-1)
    qwk = cohen_kappa_score(dy, dp, weights="quadratic", labels=list(range(10))) if len(set(dy) | set(dp)) > 1 else 0.0
    m["difficulty_qwk"] = float(qwk) if np.isfinite(qwk) else 0.0
    m["difficulty_ece"] = ece(probs["difficulty"].max(-1), dp == dy)

    sl = np.arange(11)
    m["skill_mae"] = float(np.abs(probs["skills"] @ sl - y["skills"] @ sl).mean())
    sp, sy = probs["skills"].argmax(-1), y["skills"].argmax(-1)
    m["skill_ece"] = ece(probs["skills"].max(-1), sp == sy)

    for head in ("flags", "checklist"):
        p, t = probs[head], y[head]
        m[f"{head}_f1"] = float(f1_score((t >= 0.5).ravel(), (p >= 0.5).ravel(), zero_division=0))
        m[f"{head}_macro_f1"] = float(f1_score(t >= 0.5, p >= 0.5, average="macro", zero_division=0))
        m[f"{head}_ece"] = binary_ece(p, t)
    m["flags_auroc"] = _macro_auroc(probs["flags"], y["flags"])

    q = probs["out_tokens"]
    m["out_tokens_mae"] = float(np.abs(q[:, 1] - y["out_tokens"]).mean())
    m["out_tokens_coverage80"] = float(((y["out_tokens"] >= q[:, 0]) & (y["out_tokens"] <= q[:, 2])).mean())
    m.update({f"primary_{k}": v for k, v in primary_metrics(m).items()})
    m["val_score"] = float(np.mean(list(primary_metrics(m).values())))
    return m


def primary_metrics(m: dict) -> dict:
    """One 0..100 number per head (used for the int8 '1 point' check and the val score)."""
    return {
        "category": 100 * m["category_acc"],
        "difficulty": 100 * (1 - m["difficulty_mae"] / 9),
        "skills": 100 * (1 - m["skill_mae"] / 10),
        "flags": 100 * m["flags_f1"],
        "checklist": 100 * m["checklist_f1"],
        "out_tokens": 100 * (1 - min(m["out_tokens_mae"], 4.0) / 4),
    }
