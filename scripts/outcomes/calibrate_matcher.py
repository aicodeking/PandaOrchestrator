"""Calibrate the matcher's P(success) on real attempt-and-grade outcomes, then evaluate routing on gold.

Fit on train/val attempt cells only (data/outcomes/attempts.jsonl, split != gold); gold is evaluation only.
  .venv/bin/python scripts/outcomes/calibrate_matcher.py            # diagnose + fit + eval, prints JSON summary
  .venv/bin/python scripts/outcomes/calibrate_matcher.py --apply    # also writes panda_router/matcher/calibration.json
"""

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from panda_router.eval.attempts import ATTEMPTERS, observed_cells, score_picks  # noqa: E402
from panda_router.eval.baselines import load_profiler  # noqa: E402
from panda_router.eval.gold import read_jsonl  # noqa: E402
from panda_router.eval.routing import card_price, card_strength  # noqa: E402
from panda_router.matcher import Matcher, load_cards  # noqa: E402
from panda_router.matcher.calibration import DEFAULT_PATH, card_tier, transform  # noqa: E402
from panda_router.matcher.cards import compile_pool  # noqa: E402
from panda_router.matcher.core import ability_moments, axis_weights, expected_skills, p_by_level  # noqa: E402
from panda_router.profile import TaskProfile  # noqa: E402

CACHE = ROOT / "eval_reports" / "cache"
OUT = ROOT / "data" / "outcomes"
PROFILERS = {"v2": "onnx:artifacts/panda-router-v2", "heuristic": "heuristic", "fixed_average": "fixed_average"}
TIERS = ("small", "mid")  # shifts relative to tier:strong (delta absorbs the common level)
VARIANTS = {"delta": ["delta"], "delta+slope": ["delta", "slope"], "delta+slope+a": ["delta", "slope", "a_mult"],
            "delta+slope+a+tier": ["delta", "slope", "a_mult", "small", "mid"]}
MIN_PS = (0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9)
OLD_DEFAULTS = {"min_p_success": 0.75, "floor": 0.55}  # v2 shipped defaults (uncalibrated P)
FLOOR_CAP = 0.3  # floor used in the grid: a floor above min_p would override min_p
CV_TOLERANCE = 0.005  # pick the simplest variant within this CV log-loss of the best
EPS = 1e-6


def tasks_by_id() -> dict[str, dict]:
    out = {}
    for f in ("data/train.jsonl", "data/val.jsonl", "data/gold/gold.jsonl"):
        out.update({r["id"]: r["task"] for r in read_jsonl(ROOT / f)})
    return out


def profiles(name: str, rows: list[dict], task_by_id: dict) -> dict[str, TaskProfile]:
    """Profile every task once; cached (git-ignored) because ONNX profiling dominates the runtime."""
    path = CACHE / f"calib_profiles_{re.sub(r'[^A-Za-z0-9]+', '_', PROFILERS[name])}.json"
    cached = json.loads(path.read_text()) if path.exists() else {}
    todo = [r for r in rows if r["task_id"] not in cached]
    if todo:
        prof = load_profiler(PROFILERS[name])
        tasks = [task_by_id.get(r["task_id"], {"text": r["text"], "context": {}}) for r in todo]
        done = prof.profile_batch(tasks) if hasattr(prof, "profile_batch") else [prof.profile(t) for t in tasks]
        cached.update({r["task_id"]: p.to_dict() for r, p in zip(todo, done)})
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cached))
    return {k: TaskProfile.from_dict(v) for k, v in cached.items()}


def cell_arrays(cells: list[dict], profs: dict[str, TaskProfile], pool) -> dict:
    """Raw matcher inputs per graded cell: mu, sd, a, difficulty distribution, tier, pass."""
    idx = {m: i for i, m in enumerate(pool.ids)}
    mu, sd, a, diff, tier, y, model = [], [], [], [], [], [], []
    for c in cells:
        prof, i = profs[c["task_id"]], idx[c["model"]]
        exp = expected_skills(prof.skills)
        m, s = ability_moments(axis_weights(exp), exp, pool.theta[i:i + 1], pool.se[i:i + 1])
        d = np.asarray(prof.difficulty, float)
        mu.append(m[0]), sd.append(s[0]), a.append(pool.a[i]), diff.append(d / d.sum())
        tier.append(card_tier(pool.cards[i])), y.append(float(c["pass"])), model.append(c["model"])
    return {"mu": np.array(mu), "sd": np.array(sd), "a": np.array(a), "diff": np.array(diff),
            "tier": np.array(tier, dtype=object), "y": np.array(y), "model": np.array(model),
            "task": np.array([c["task_id"] for c in cells])}


def params_from(vec, names) -> dict:
    p = {"delta": 0.0, "slope": 1.0, "a_mult": 1.0, "tier_shift": {}}
    for n, v in zip(names, vec):
        if n in TIERS:
            p["tier_shift"][n] = float(v)
        elif n in ("slope", "a_mult"):
            p[n] = float(np.exp(v))  # log-parametrised: stays > 0
        else:
            p[n] = float(v)
    return p


def predict(X: dict, cal: dict | None, sel=slice(None)) -> np.ndarray:
    shift = np.array([(cal or {}).get("tier_shift", {}).get(t, 0.0) for t in X["tier"][sel]])
    mu, sd, a = transform(X["mu"][sel], X["sd"][sel], X["a"][sel], shift, cal)
    return np.clip((p_by_level(mu, sd, a) * X["diff"][sel]).sum(1), EPS, 1 - EPS)


def nll(p, y) -> float:
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def fit(X: dict, names: list[str], sel=slice(None)) -> dict:
    y = X["y"][sel]
    res = minimize(lambda v: nll(predict(X, params_from(v, names), sel), y), np.zeros(len(names)),
                   method="Nelder-Mead", options={"xatol": 1e-4, "fatol": 1e-7, "maxiter": 4000})
    return params_from(res.x, names)


def cv(X: dict, names: list[str], k: int = 5, seed: int = 0) -> float:
    """Task-grouped k-fold CV log-loss (all cells of a task stay in one fold)."""
    tasks = np.unique(X["task"])
    fold = dict(zip(np.random.default_rng(seed).permutation(tasks), np.arange(len(tasks)) % k))
    f = np.array([fold[t] for t in X["task"]])
    losses = np.zeros(len(f))
    for j in range(k):
        cal = fit(X, names, f != j) if names else None
        p = predict(X, cal, f == j)
        losses[f == j] = -(X["y"][f == j] * np.log(p) + (1 - X["y"][f == j]) * np.log(1 - p))
    return float(losses.mean())


def metrics(p, y, bins: int = 10) -> dict:
    b = np.minimum((p * bins).astype(int), bins - 1)
    ece = sum(abs(p[b == i].mean() - y[b == i].mean()) * (b == i).mean() for i in range(bins) if (b == i).any())
    return {"n": int(len(y)), "brier": round(float(np.mean((p - y) ** 2)), 4), "logloss": round(nll(p, y), 4),
            "ece": round(float(ece), 4), "mean_p": round(float(p.mean()), 3), "pass_rate": round(float(y.mean()), 3)}


def per_model(X: dict, p: np.ndarray) -> dict:
    return {m.split("-", 1)[1]: {"mean_p": round(float(p[X["model"] == m].mean()), 3),
                                 "pass": round(float(X["y"][X["model"] == m].mean()), 3), "n": int((X["model"] == m).sum())}
            for m in ATTEMPTERS}


def reliability(X: dict, p: np.ndarray, edges=(0, .2, .4, .6, .8, .9, 1.0001)) -> list:
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        s = (p >= lo) & (p < hi)
        if s.any():
            out.append({"bin": f"{lo:.1f}-{min(hi, 1):.1f}", "n": int(s.sum()), "mean_p": round(float(p[s].mean()), 3),
                        "pass": round(float(X["y"][s].mean()), 3)})
    return out


def difficulty_slope(X: dict) -> dict:
    ed = X["diff"] @ np.arange(1, 11)
    M = np.stack([X["model"] == m for m in ATTEMPTERS], 1).astype(float)
    D = np.column_stack([M, ed - ed.mean()])

    def f(w):
        z = D @ w
        return float(np.mean(np.logaddexp(0, z) - X["y"] * z))

    w = minimize(f, np.zeros(D.shape[1]), method="BFGS").x
    return {"logit_per_difficulty_level": round(float(w[-1]), 3), "expected_difficulty_mean": round(float(ed.mean()), 2),
            "expected_difficulty_sd": round(float(ed.std()), 2)}


def route_eval(profs, tasks, task_by_id, cells, cal, cards_dir=None) -> dict:
    """Routed success/cost on tasks with all 5 cells graded. Grid rows use floor = min(min_p, FLOOR_CAP)."""
    m = Matcher(cards_dir=cards_dir, calibration=cal if cal is not None else False)
    configs = {"old_defaults(0.75, floor 0.55)": {"mode": "cheapest_above_threshold", **OLD_DEFAULTS}}
    configs |= {f"min_p={mp}": {"mode": "cheapest_above_threshold", "min_p_success": mp, "floor": min(mp, FLOOR_CAP)}
                for mp in MIN_PS}
    configs |= {"max_utility": {"mode": "max_utility", "floor": FLOOR_CAP}, "max_quality": {"mode": "max_quality"}}
    out = {}
    for name, prefs in configs.items():
        picks = {t: m.route({"task": task_by_id.get(t, {"text": "", "context": {}}), "pool": list(ATTEMPTERS),
                             "preferences": prefs}, profs[t], trace_id="calib")["choice"]["model_id"] for t in tasks}
        out[name] = score_picks(picks, cells)
    return out


def gain_over_mix(row: dict, base: dict) -> float:
    """Success above the line that randomly mixes always-cheapest and always-strongest at the same cost."""
    lo, hi = base["always_cheapest"], base["always_strongest"]
    slope = (hi["success_per_100"] - lo["success_per_100"]) / (hi["cost_per_100_usd"] - lo["cost_per_100_usd"])
    return row["success_per_100"] - (lo["success_per_100"] + slope * (row["cost_per_100_usd"] - lo["cost_per_100_usd"]))


def choose_min_p(routing: dict, base: dict) -> float:
    """Largest gain over the cheap/strong mixing line; ties -> higher min_p (more success)."""
    grid = [(gain_over_mix(routing[f"min_p={mp}"], base), mp) for mp in MIN_PS]
    return max(grid)[1]


def baselines(gold_tasks, cells, cards) -> dict:
    strongest = max(ATTEMPTERS, key=lambda x: (card_strength(cards[x]), x))
    cheapest = min(ATTEMPTERS, key=lambda x: (card_price(cards[x]), x))
    out = {"always_cheapest": score_picks({t: cheapest for t in gold_tasks}, cells),
           "always_strongest": score_picks({t: strongest for t in gold_tasks}, cells)}
    for mod in ATTEMPTERS:
        out[f"always_{mod.split('-', 1)[1]}"] = score_picks({t: mod for t in gold_tasks}, cells)
    oracle = {}
    for t in gold_tasks:
        passed = [x for x in ATTEMPTERS if cells[(t, x)]["pass"]]
        pool = passed or list(ATTEMPTERS)
        oracle[t] = min(pool, key=lambda x: cells[(t, x)]["cost_attempt"])
    out["oracle"] = score_picks(oracle, cells)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write the chosen v2 fit to calibration.json")
    ap.add_argument("--variant", default=None, help="force a variant (default: simplest within CV_TOLERANCE)")
    ap.add_argument("--cards", default=None, help="what-if cards dir (default: cards/); --apply needs the default")
    ap.add_argument("--profiler", default=PROFILERS["v2"], help="profiler the shipped fit is for (e.g. onnx:artifacts/panda-router-v3)")
    args = ap.parse_args()
    PROFILERS["v2"] = args.profiler

    attempts = read_jsonl(OUT / "attempts.jsonl")
    train_cells = [r for r in attempts if r["split"] != "gold" and r.get("pass") is not None and r["model"] in ATTEMPTERS]
    gold_cells = observed_cells(attempts)
    gold_rows = read_jsonl(OUT / "gold_attempts.jsonl")
    gold_tasks = [r["task_id"] for r in gold_rows if all((r["task_id"], m) in gold_cells for m in ATTEMPTERS)]
    gold_list = [gold_cells[(t, m)] for t in gold_tasks for m in ATTEMPTERS]
    task_rows = read_jsonl(OUT / "tasks_attempts.jsonl") + gold_rows
    task_by_id = tasks_by_id()
    if args.apply and args.cards:
        raise SystemExit("--apply fits must use the shipped cards/")
    cards = load_cards(args.cards)
    pool = compile_pool([cards[m] for m in ATTEMPTERS])
    train_index = {(c["task_id"], c["model"]): c for c in train_cells}
    train_full = sorted({t for t, _ in train_index if all((t, m) in train_index for m in ATTEMPTERS)})

    summary = {"n_train_cells": len(train_cells), "n_train_tasks": len({c["task_id"] for c in train_cells}),
               "n_gold_tasks": len(gold_tasks), "n_train_full_tasks": len(train_full),
               "baselines": baselines(gold_tasks, gold_cells, cards),
               "train_baselines": baselines(train_full, train_index, cards), "profilers": {}}
    for name in PROFILERS:
        profs = profiles(name, task_rows, task_by_id)
        Xt, Xg = cell_arrays(train_cells, profs, pool), cell_arrays(gold_list, profs, pool)
        cvs = {"none": round(cv(Xt, []), 4), **{v: round(cv(Xt, n), 4) for v, n in VARIANTS.items()}}
        best = args.variant or next(v for v in VARIANTS if cvs[v] <= min(cvs.values()) + CV_TOLERANCE)
        cal = fit(Xt, VARIANTS[best])
        p0t, p1t, p0g, p1g = predict(Xt, None), predict(Xt, cal), predict(Xg, None), predict(Xg, cal)
        summary["profilers"][name] = {
            "cv_logloss": cvs, "variant": best, "params": cal,
            "fits": {v: fit(Xt, n) for v, n in VARIANTS.items()},
            "train": {"before": metrics(p0t, Xt["y"]), "after": metrics(p1t, Xt["y"]),
                      "per_model_before": per_model(Xt, p0t), "per_model_after": per_model(Xt, p1t),
                      "reliability_before": reliability(Xt, p0t), "reliability_after": reliability(Xt, p1t),
                      "difficulty_signal": difficulty_slope(Xt)},
            "gold": {"before": metrics(p0g, Xg["y"]), "after": metrics(p1g, Xg["y"]),
                     "per_model_before": per_model(Xg, p0g), "per_model_after": per_model(Xg, p1g),
                     "difficulty_signal": difficulty_slope(Xg)},
            "train_routing_calibrated": route_eval(profs, train_full, task_by_id, train_index, cal, args.cards),
            "routing_uncalibrated": route_eval(profs, gold_tasks, task_by_id, gold_cells, None, args.cards),
            "routing_calibrated": route_eval(profs, gold_tasks, task_by_id, gold_cells, cal, args.cards),
        }
        P = summary["profilers"][name]
        P["chosen_min_p_on_train"] = choose_min_p(P["train_routing_calibrated"], summary["train_baselines"])
        P["gain_over_mix_gold"] = {k: round(gain_over_mix(v, summary["baselines"]), 1)
                                   for k, v in P["routing_calibrated"].items()}
        print(name, best, json.dumps(cal), P["chosen_min_p_on_train"], file=sys.stderr)

    (CACHE / f"calibration_summary{'_whatif' if args.cards else ''}.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))
    if args.apply:
        v2 = summary["profilers"]["v2"]
        DEFAULT_PATH.write_text(json.dumps({"params": v2["params"], "provenance": {
            "fitted_by": "scripts/outcomes/calibrate_matcher.py", "date": dt.date.today().isoformat(),
            "data": "data/outcomes/attempts.jsonl (split train+val, gold excluded)",
            "n_cells": summary["n_train_cells"], "n_tasks": summary["n_train_tasks"],
            "profiler": args.profiler, "cards": "cards/ at fit time (5 OpenRouter attempters)",
            "variant": v2["variant"], "cv_logloss": v2["cv_logloss"],
            "judge": "deepseek-v4.1-flash, reasoning effort low (kappa 0.85 vs kimi-k3.1-pro)",
            "report": "data/outcomes/REPORT_calibration.md"}}, indent=2) + "\n")


if __name__ == "__main__":
    main()
