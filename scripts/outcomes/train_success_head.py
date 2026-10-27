"""Train the v4 success head P(pass | task, model) on graded train/val attempts (gold never used).

  .venv/bin/python scripts/outcomes/train_success_head.py --profiler artifacts/panda-router-v4 \
      --out artifacts/panda-router-v4/success_head.json

Frozen features = the profiler's TaskProfile (+ widened difficulty, length). Joint logistic over the 9 attempter
card ids (shared + per-card weights), failures up-weighted (--fail-weight, penalises over-predicting success),
C chosen by 5-fold task-grouped CV log-loss. Writes the head, out-of-fold predictions for policy tuning
(<cache>/success_oof_<profiler>.jsonl) and CV metrics (in the head json under "cv").
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from panda_router.matcher import ability_moments, axis_weights, compile_pool, expected_skills, load_cards  # noqa: E402
from panda_router.matcher.core import p_by_level  # noqa: E402
from panda_router.model.onnx_profiler import OnnxProfiler  # noqa: E402
from panda_router.router_v4.policy import logit, p_at_level  # noqa: E402
from panda_router.profile import TaskProfile  # noqa: E402
from panda_router.router_v4.success import (feature_names, quantile_level, task_features,  # noqa: E402
                                            vagueness, widen_difficulty)

CELLS = ROOT / "data/outcomes/success_cells.jsonl"
FOLDS = 5


def read_jsonl(p):
    return [json.loads(ln) for ln in Path(p).read_text().splitlines() if ln.strip()]


def profiles_for(profiler_dir: str, texts: dict[str, str], cache: Path) -> dict[str, TaskProfile]:
    """task_id -> TaskProfile, cached per profiler artifact (text-only input, as PandaCode sends)."""
    tag = Path(profiler_dir).resolve().name
    f = cache / f"profiles_{tag}.json"
    got = json.loads(f.read_text()) if f.exists() else {}
    todo = [t for t in texts if t not in got]
    if todo:
        prof = OnnxProfiler(profiler_dir)
        for i in range(0, len(todo), 32):
            ids = todo[i:i + 32]
            for tid, p in zip(ids, prof.profile_batch([{"text": texts[t], "context": {}} for t in ids])):
                got[tid] = p.to_dict()
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(got))
    return {t: TaskProfile.from_dict(got[t]) for t in texts}


def design(X: np.ndarray, m: np.ndarray, n_models: int) -> np.ndarray:
    """[one-hot model | shared x | x (x) one-hot model]."""
    oh = np.eye(n_models)[m]
    return np.hstack([oh, X, (X[:, None, :] * oh[:, :, None]).reshape(len(X), -1)])


def fit(Z, y, w, C):
    clf = LogisticRegression(C=C, max_iter=3000, fit_intercept=True)
    clf.fit(Z, y, sample_weight=w)
    return clf


def to_params(clf, n_models: int, d: int) -> tuple[np.ndarray, np.ndarray]:
    c = clf.coef_[0]
    bias = clf.intercept_[0] + c[:n_models]
    coef = c[n_models:n_models + d][None, :] + c[n_models + d:].reshape(n_models, d)
    return coef, bias


def card_p_q(profile: TaskProfile, diff: np.ndarray, pool, row: int, q: float) -> float:
    """Raw card-IRT P for one card at the q-quantile of the (widened) difficulty."""
    exp = expected_skills(profile.skills)
    mu, sd = ability_moments(axis_weights(exp), exp, pool.theta[row:row + 1], pool.se[row:row + 1])
    return float(p_at_level(p_by_level(mu, sd, pool.a[row:row + 1]), quantile_level(diff, q))[0])


def card_calibration(cells, profiles, texts, cards, a, prior) -> dict:
    """pass ~ sigmoid(alpha + beta * logit(P_card_q)), failures up-weighted; leave-one-card-out check of the
    mapping on a card it never saw (how uncovered cards are scored)."""
    pool = compile_pool([load_cards()[c] for c in cards])
    rows = []
    for r in cells:
        p = profiles[r["task_id"]]
        v = vagueness(p, texts[r["task_id"]], a.short_words)
        d = widen_difficulty(p.difficulty, a.omega_max * v, prior)
        rows.append(card_p_q(p, d, pool, cards.index(r["card_id"]), a.quantile))
    x = logit(np.array(rows))[:, None]
    y = np.array([int(r["pass"]) for r in cells])
    w = np.where(y == 1, 1.0, a.fail_weight)
    cid = np.array([r["card_id"] for r in cells])
    loco = {}
    for c in cards:
        tr = cid != c
        clf = LogisticRegression(C=1.0).fit(x[tr], y[tr], sample_weight=w[tr])
        loco[c] = {"pred": round(float(clf.predict_proba(x[~tr])[:, 1].mean()), 3), "actual": round(float(y[~tr].mean()), 3)}
    clf = LogisticRegression(C=1.0).fit(x, y, sample_weight=w)
    auc = roc_auc_score(y, x[:, 0])
    return {"alpha": float(clf.intercept_[0]), "beta": float(clf.coef_[0, 0]), "raw_card_auc": round(float(auc), 4),
            "raw_card_mean_p": round(float(np.mean(rows)), 4), "leave_one_card_out": loco}


def fit_platt(L, m, y, n_cards) -> list[list[float]]:
    """Per card [a, b]: P = sigmoid(a + b * logit)."""
    out = []
    for j in range(n_cards):
        s = m == j
        clf = LogisticRegression(C=10.0, max_iter=2000).fit(L[s, None], y[s])
        out.append([float(clf.intercept_[0]), max(float(clf.coef_[0, 0]), 0.05)])
    return out


def apply_platt(platt, L, S, m, z):
    a = np.array([platt[j][0] for j in m])
    b = np.array([platt[j][1] for j in m])
    sig = lambda x: 1 / (1 + np.exp(-x))  # noqa: E731
    return sig(a + b * L), sig(a + b * (L - z * S))


def ece(p, y, n=10) -> float:
    b = np.minimum((p * n).astype(int), n - 1)
    return round(float(sum(abs(p[b == k].mean() - y[b == k].mean()) * (b == k).mean() for k in range(n) if (b == k).any())), 4)


def reliability(p, y, n=10) -> list[dict]:
    b = np.minimum((p * n).astype(int), n - 1)
    return [{"bin": f"{k / n:.1f}-{(k + 1) / n:.1f}", "n": int((b == k).sum()), "mean_p": round(float(p[b == k].mean()), 3),
             "pass": round(float(y[b == k].mean()), 3)} for k in range(n) if (b == k).any()]


def escalation_logits(cells, cards) -> dict:
    """adj[A][B] = logit P(B passes | A failed) - logit P(B passes), on tasks both attempted (+1/+2 smoothing)."""
    res = defaultdict(dict)
    for r in cells:
        res[r["task_id"]][r["card_id"]] = int(r["pass"])
    adj = {}
    for A in cards:
        adj[A] = {}
        for B in cards:
            if A == B:
                continue
            both = [d for d in res.values() if A in d and B in d]
            pb = (sum(d[B] for d in both) + 1) / (len(both) + 2)
            fail = [d for d in both if not d[A]]
            pbf = (sum(d[B] for d in fail) + 1) / (len(fail) + 2)
            adj[A][B] = round(float(logit(pbf) - logit(pb)), 4)
    return adj


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profiler", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", default=str(ROOT / "checkpoints/v4/success"))
    ap.add_argument("--fail-weight", type=float, default=1.0,
                    help=">1 up-weights failures (v4.0 used 2.5; it deflated P, so v4.1 calibrates and uses a bound)")
    ap.add_argument("--C", default="0.01,0.03,0.1,0.3")
    ap.add_argument("--bootstrap", type=int, default=16)
    ap.add_argument("--quantile", type=float, default=0.75)
    ap.add_argument("--omega-max", type=float, default=0.7)
    ap.add_argument("--short-words", type=float, default=12)
    ap.add_argument("--lcb-z", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    cells = [r for r in read_jsonl(CELLS) if r["split"] in ("train", "val")]  # gold: evaluation only
    texts = {r["task_id"]: r["text"] for r in cells}
    profiles = profiles_for(a.profiler, texts, Path(a.cache))
    # population prior: mean raw difficulty over train tasks
    prior = np.mean([profiles[t].difficulty for t in texts], axis=0)
    prior = prior / prior.sum()

    cards = sorted({r["card_id"] for r in cells})
    cidx = {c: i for i, c in enumerate(cards)}

    def feats(tid):
        p = profiles[tid]
        v = vagueness(p, texts[tid], a.short_words)
        return task_features(p, texts[tid], widen_difficulty(p.difficulty, a.omega_max * v, prior), a.quantile, v)

    F = {t: feats(t) for t in texts}
    X = np.array([F[r["task_id"]] for r in cells])
    mu, sd = X.mean(0), X.std(0) + 1e-6
    Xs = (X - mu) / sd
    m = np.array([cidx[r["card_id"]] for r in cells])
    y = np.array([int(r["pass"]) for r in cells])
    w = np.where(y == 1, 1.0, a.fail_weight)
    Z = design(Xs, m, len(cards))
    d = X.shape[1]

    rng = np.random.default_rng(a.seed)
    tasks = sorted(texts)
    fold_of = dict(zip(tasks, rng.permutation(len(tasks)) % FOLDS))
    fold = np.array([fold_of[r["task_id"]] for r in cells])

    cv = {}
    oof_by_C = {}
    for C in map(float, a.C.split(",")):
        oof = np.zeros(len(y))
        for k in range(FOLDS):
            tr, te = fold != k, fold == k
            oof[te] = fit(Z[tr], y[tr], w[tr], C).predict_proba(Z[te])[:, 1]
        cv[C] = {"logloss": round(log_loss(y, oof), 4), "auc": round(roc_auc_score(y, oof), 4),
                 "mean_p": round(float(oof.mean()), 4), "pass_rate": round(float(y.mean()), 4)}
        oof_by_C[C] = oof
        print(f"C={C}: {cv[C]}", flush=True)
    best_C = min(cv, key=lambda c: cv[c]["logloss"])

    # OOF bootstrap logits at best C for the LCB (policy tuning uses these, never gold)
    oof_L = np.zeros((a.bootstrap, len(y)))
    for k in range(FOLDS):
        tr_tasks = [t for t in tasks if fold_of[t] != k]
        te = fold == k
        for b in range(a.bootstrap):
            pick = set(rng.choice(tr_tasks, size=len(tr_tasks), replace=True))
            sel = np.array([(fold_of[r["task_id"]] != k) and (r["task_id"] in pick) for r in cells])
            oof_L[b, te] = fit(Z[sel], y[sel], w[sel], best_C).decision_function(Z[te])
    oof_mean, oof_sd = oof_L.mean(0), oof_L.std(0)

    # per-card Platt calibration of the bootstrap-mean logit; nested (fit on the other folds' OOF) for reporting
    cal_p, cal_lo = np.zeros(len(y)), np.zeros(len(y))
    for k in range(FOLDS):
        tr, te = fold != k, fold == k
        pl = fit_platt(oof_mean[tr], m[tr], y[tr], len(cards))
        cal_p[te], cal_lo[te] = apply_platt(pl, oof_mean[te], oof_sd[te], m[te], a.lcb_z)
    platt = fit_platt(oof_mean, m, y, len(cards))
    raw_p = 1 / (1 + np.exp(-oof_mean))
    calibration = {
        "method": "per-card Platt on out-of-fold bootstrap-mean logits; lower bound = Platt(mean - z*sd)",
        "raw": {"ece": ece(raw_p, y), "logloss": round(log_loss(y, raw_p), 4), "mean_p": round(float(raw_p.mean()), 4)},
        "calibrated_nested_cv": {"ece": ece(cal_p, y), "logloss": round(log_loss(y, cal_p), 4),
                                 "auc": round(roc_auc_score(y, cal_p), 4), "mean_p": round(float(cal_p.mean()), 4),
                                 "mean_margin": round(float((cal_p - cal_lo).mean()), 4),
                                 "reliability": reliability(cal_p, y)},
        "pass_rate": round(float(y.mean()), 4)}
    print("calibration:", json.dumps({k: v for k, v in calibration.items() if k != "method"}), flush=True)

    per_card = defaultdict(dict)
    for c, i in cidx.items():
        s = m == i
        per_card[c] = {"n": int(s.sum()), "pass": round(float(y[s].mean()), 3),
                       "auc": round(roc_auc_score(y[s], oof_by_C[best_C][s]), 3) if 0 < y[s].mean() < 1 else None}

    coefs, biases = [], []
    for b in range(a.bootstrap):
        pick = rng.choice(tasks, size=len(tasks), replace=True)
        cnt = defaultdict(int)
        for t in pick:
            cnt[t] += 1
        wb = w * np.array([cnt[r["task_id"]] for r in cells])
        sel = wb > 0
        c_, b_ = to_params(fit(Z[sel], y[sel], wb[sel], best_C), len(cards), d)
        coefs.append(c_.tolist())
        biases.append(b_.tolist())

    # population base rate per card: mean calibrated P over ALL train/val tasks (comparable across cards, unlike
    # per-card pass rates on the different task subsets each card was attempted on)
    XT = (np.array([F[t] for t in tasks]) - mu) / sd
    Lall = np.mean([XT @ np.asarray(c_).T + np.asarray(b_) for c_, b_ in zip(coefs, biases)], axis=0)  # (T, M)
    base_rate = {c: round(float(np.mean(1 / (1 + np.exp(-(platt[i][0] + platt[i][1] * Lall[:, i]))))), 4)
                 for c, i in cidx.items()}
    print("base rates:", base_rate, flush=True)

    card_cal = card_calibration(cells, profiles, texts, cards, a, prior)
    print("card calibration:", json.dumps(card_cal), flush=True)

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    params = {
        "name": f"success_head_v4({Path(a.profiler).resolve().name})", "cards": cards,
        "feature_names": feature_names(), "mu": mu.tolist(), "sd": sd.tolist(), "coef": coefs, "bias": biases,
        "prior_difficulty": prior.tolist(), "difficulty_quantile": a.quantile, "lcb_z": a.lcb_z,
        "omega_max": a.omega_max, "short_words": a.short_words, "fail_weight": a.fail_weight,
        "platt": {c: platt[i] for c, i in cidx.items()},
        "base_rate": base_rate,
        "calibration": calibration,
        "card_calibration": card_cal,
        "escalation_logit": escalation_logits(cells, cards),
        "trained_on": "data/outcomes/success_cells.jsonl splits train+val (gold excluded)",
        "cv": {"folds": FOLDS, "by_C": {str(k): v for k, v in cv.items()}, "best_C": best_C,
               "per_card": per_card, "n_cells": len(y), "n_tasks": len(tasks)},
    }
    out.write_text(json.dumps(params))
    oof_path = Path(a.cache) / f"success_oof_{Path(a.profiler).resolve().name}.jsonl"
    with oof_path.open("w") as f:
        for r, lm, ls, pc, pl in zip(cells, oof_mean, oof_sd, cal_p, cal_lo):
            f.write(json.dumps({"task_id": r["task_id"], "card_id": r["card_id"], "pass": r["pass"],
                                "logit": round(float(lm), 4), "logit_sd": round(float(ls), 4),
                                "p": round(float(pc), 4), "p_lower": round(float(pl), 4)}) + "\n")
    print(f"best C={best_C} {cv[best_C]}; wrote {out}")


if __name__ == "__main__":
    main()
