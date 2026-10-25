"""Profiler metrics: predicted TaskProfile dicts vs CONTRACTS.md soft labels.

Every function takes plain python/numpy inputs so it can be unit-tested on synthetic data.
Hard targets are derived from soft labels: argmax for category, expected level (rounded for QWK)
for ordinal heads, >= 0.5 for flags/checklist.
"""

from __future__ import annotations

import math

import numpy as np

from ..taxonomy import CATEGORIES, CHECKLIST_IDS, FLAGS, SKILL_AXES

DIFF_LEVELS = np.arange(1, 11, dtype=float)
SKILL_LEVELS = np.arange(0, 11, dtype=float)


# --------------------------------------------------------------------------- primitives
def cat_vector(d: dict[str, float]) -> np.ndarray:
    v = np.array([float(d.get(c, 0.0)) for c in CATEGORIES])
    s = v.sum()
    return v / s if s > 0 else np.full(len(CATEGORIES), 1.0 / len(CATEGORIES))


def expected(dist, levels: np.ndarray) -> float:
    d = np.asarray(dist, dtype=float)
    return float(d @ levels / d.sum())


def spearman(x, y) -> float | None:
    from scipy.stats import spearmanr

    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 3 or np.all(x == x[0]) or np.all(y == y[0]):
        return None
    return float(spearmanr(x, y).statistic)


def qwk(y_true, y_pred, labels=None) -> float | None:
    from sklearn.metrics import cohen_kappa_score

    y_true, y_pred = np.asarray(y_true, int), np.asarray(y_pred, int)
    if len(set(y_true.tolist()) | set(y_pred.tolist())) < 2:
        return None
    return float(cohen_kappa_score(y_true, y_pred, weights="quadratic", labels=labels))


def f1_binary(y_true, y_pred) -> float | None:
    y_true, y_pred = np.asarray(y_true, bool), np.asarray(y_pred, bool)
    tp = float(np.sum(y_true & y_pred))
    fp = float(np.sum(~y_true & y_pred))
    fn = float(np.sum(y_true & ~y_pred))
    if tp + fp + fn == 0:
        return None  # no positives anywhere: undefined
    return 2 * tp / (2 * tp + fp + fn)


def auroc(y_true, scores) -> float | None:
    from sklearn.metrics import roc_auc_score

    y_true = np.asarray(y_true, int)
    if y_true.min() == y_true.max():
        return None
    return float(roc_auc_score(y_true, np.asarray(scores, float)))


def ece(confidence, correct, n_bins: int = 10) -> float | None:
    """Expected calibration error with equal-width bins: sum_b |B|/N * |acc_b - conf_b|."""
    conf, corr = np.asarray(confidence, float), np.asarray(correct, float)
    if len(conf) == 0:
        return None
    bins = np.minimum((conf * n_bins).astype(int), n_bins - 1)
    total = 0.0
    for b in range(n_bins):
        m = bins == b
        if m.any():
            total += m.sum() / len(conf) * abs(corr[m].mean() - conf[m].mean())
    return float(total)


def binary_ece(probs, targets, n_bins: int = 10) -> float | None:
    """Reliability of a Bernoulli head: bin predicted P(1) and compare with the mean (soft) target."""
    return ece(probs, targets, n_bins)


def _mean(xs) -> float | None:
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return float(np.mean(xs)) if xs else None


def _r(x, nd: int = 4):
    return None if x is None else round(float(x), nd)


# --------------------------------------------------------------------------- heads
def category_metrics(labels: list[dict], preds: list[dict]) -> dict:
    L = np.stack([cat_vector(l) for l in labels])
    P = np.stack([cat_vector(p) for p in preds])
    yt = L.argmax(1)
    top = np.argsort(-P, axis=1)
    acc = float(np.mean(top[:, 0] == yt))
    top2 = float(np.mean([(yt[i] in top[i, :2]) for i in range(len(yt))]))
    soft_ce = float(np.mean(-(L * np.log(np.clip(P, 1e-9, 1))).sum(1)))
    per_cat = {}
    for k, c in enumerate(CATEGORIES):
        m = yt == k
        if m.any():
            per_cat[c] = {"n": int(m.sum()), "recall": _r(np.mean(top[m, 0] == k))}
    conf = P.max(1)
    return {"acc": _r(acc), "top2": _r(top2), "soft_ce": _r(soft_ce),
            "ece": _r(ece(conf, top[:, 0] == yt)), "per_category": per_cat}


def difficulty_metrics(labels: list[list[float]], preds: list[list[float]], anchors: list[float | None] | None = None) -> dict:
    el = np.array([expected(d, DIFF_LEVELS) for d in labels])
    ep = np.array([expected(d, DIFF_LEVELS) for d in preds])
    P = np.array([np.asarray(d, float) / np.sum(d) for d in preds])
    L = np.array([np.asarray(d, float) / np.sum(d) for d in labels])
    out = {
        "mae": _r(np.mean(np.abs(el - ep))),
        "spearman": _r(spearman(el, ep)),
        "qwk": _r(qwk(np.rint(el), np.rint(ep), labels=list(range(1, 11)))),
        "label_mean": _r(el.mean(), 3), "pred_mean": _r(ep.mean(), 3),
        "ece": _r(ece(P.max(1), P.argmax(1) == L.argmax(1))),
    }
    if anchors is not None:
        idx = [i for i, a in enumerate(anchors) if a is not None]
        if len(idx) >= 3:
            a = np.array([anchors[i] for i in idx], float)
            out["anchor_n"] = len(idx)
            out["spearman_pred_vs_anchor"] = _r(spearman(ep[idx], a))
            out["spearman_label_vs_anchor"] = _r(spearman(el[idx], a))
    return out


def skill_metrics(labels: list[dict], preds: list[dict]) -> dict:
    per, eces = {}, {}
    for ax in SKILL_AXES:
        el = np.array([expected(l[ax], SKILL_LEVELS) for l in labels])
        ep = np.array([expected(p[ax], SKILL_LEVELS) for p in preds])
        P = np.array([np.asarray(p[ax], float) / np.sum(p[ax]) for p in preds])
        L = np.array([np.asarray(l[ax], float) / np.sum(l[ax]) for l in labels])
        per[ax] = {"mae": _r(np.mean(np.abs(el - ep))), "spearman": _r(spearman(el, ep))}
        eces[ax] = ece(P.max(1), P.argmax(1) == L.argmax(1))
    return {"mae_mean": _r(_mean(v["mae"] for v in per.values())),
            "spearman_mean": _r(_mean(v["spearman"] for v in per.values())),
            "ece_mean": _r(_mean(eces.values())), "per_axis": per}


def binary_head_metrics(labels: list[dict], preds: list[dict], ids: list[str]) -> dict:
    per, all_t, all_p = {}, [], []
    for k in ids:
        t = np.array([float(l.get(k, 0.0)) for l in labels])
        p = np.array([float(q.get(k, 0.0)) for q in preds])
        all_t.append(t >= 0.5)
        all_p.append(p >= 0.5)
        per[k] = {"pos_rate": _r(np.mean(t >= 0.5)), "f1": _r(f1_binary(t >= 0.5, p >= 0.5)),
                  "auroc": _r(auroc(t >= 0.5, p)), "ece": _r(binary_ece(p, t)),
                  "brier": _r(np.mean((p - t) ** 2))}
    micro = f1_binary(np.concatenate(all_t), np.concatenate(all_p)) if ids else None
    return {"f1_macro": _r(_mean(v["f1"] for v in per.values())), "f1_micro": _r(micro),
            "auroc_macro": _r(_mean(v["auroc"] for v in per.values())),
            "ece_macro": _r(_mean(v["ece"] for v in per.values())),
            "brier_macro": _r(_mean(v["brier"] for v in per.values())), "per_id": per}


def out_tokens_metrics(labels: list[float], preds: list[dict]) -> dict:
    t = np.asarray(labels, float)
    p50 = np.array([float(p.get("p50", 3.0)) for p in preds])
    p10 = np.array([float(p.get("p10", p.get("p50", 3.0))) for p in preds])
    p90 = np.array([float(p.get("p90", p.get("p50", 3.0))) for p in preds])
    return {"mae_log10": _r(np.mean(np.abs(t - p50))), "spearman": _r(spearman(t, p50)),
            "coverage_p10_p90": _r(np.mean((t >= p10) & (t <= p90)))}


def profiler_metrics(labels: list[dict], preds: list[dict], anchors: list[float | None] | None = None) -> dict:
    """labels: CONTRACTS.md `labels` dicts. preds: TaskProfile.to_dict() dicts."""
    assert len(labels) == len(preds) and labels, "need equal, non-empty label/pred lists"
    flags = binary_head_metrics([l["flags"] for l in labels], [p["flags"] for p in preds], FLAGS)
    check = binary_head_metrics([l["checklist"] for l in labels], [p["checklist"] for p in preds], CHECKLIST_IDS)
    m = {
        "n": len(labels),
        "category": category_metrics([l["category"] for l in labels], [p["category"] for p in preds]),
        "difficulty": difficulty_metrics([l["difficulty"] for l in labels], [p["difficulty"] for p in preds], anchors),
        "skills": skill_metrics([l["skills"] for l in labels], [p["skills"] for p in preds]),
        "flags": flags,
        "checklist": check,
        "out_tokens": out_tokens_metrics([l["out_tokens_log10"] for l in labels], [p["out_tokens_log10"] for p in preds]),
    }
    m["ece"] = {"category": m["category"]["ece"], "difficulty": m["difficulty"]["ece"],
                "skills_mean": m["skills"]["ece_mean"], "flags_macro": flags["ece_macro"],
                "checklist_macro": check["ece_macro"]}
    return m
