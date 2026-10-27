"""v4 router: tune the policy on train/val (out-of-fold success-head predictions) and evaluate on held-out gold.

  .venv/bin/python scripts/eval/v4_eval.py tune  --out eval_reports/v4/tune.json
  .venv/bin/python scripts/eval/v4_eval.py gold  --out eval_reports/v4/gold.json

tune: grid over the failure penalty L ($), min_p, cost weight and the LCB z on train/val tasks, using out-of-fold
      head logits (checkpoints/v4/success/success_oof_<profiler>.jsonl), so no task is scored by a head that saw it.
gold: the shipped Matcher (v4 head + policy) vs the v3 profiler/policy, single models, always-cheapest/-strongest,
      oracle, and a cascade (1-2 retries, judge label as the failure signal), with bootstrap 95% CIs over tasks.
Outcomes and $ are real: judge pass/fail and logged attempt cost (failed attempts included in cascade $).
"""

import argparse
import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from panda_router.eval.routing import card_price, card_strength  # noqa: E402
from panda_router.matcher import estimate_input_tokens, load_cards  # noqa: E402
from panda_router.outcomes.grade import ATTEMPT_SYSTEM  # noqa: E402
from panda_router.profile import TaskProfile  # noqa: E402
from panda_router.router_v4.policy import choose, free_guard, ladder  # noqa: E402

CELLS = ROOT / "data/outcomes/success_cells.jsonl"
ATTEMPTS = ROOT / "data/outcomes/attempts.jsonl"
SUB4 = ("claude-haiku-5.5", "claude-sonnet-5.5", "claude-opus-5.5", "codex-gpt-6-luna")
MODES = ("cheapest_above_threshold", "max_utility", "max_quality")


def read_jsonl(p):
    return [json.loads(ln) for ln in Path(p).read_text().splitlines() if ln.strip()]


def outcomes(split: set[str]):
    """task_id -> {card: pass}, task_id -> text, (task, card) -> real attempt $."""
    res, text = defaultdict(dict), {}
    for r in read_jsonl(CELLS):
        if r["split"] in split:
            res[r["task_id"]][r["card_id"]] = int(r["pass"])
            text[r["task_id"]] = r["text"]
    cards = load_cards()
    cost = {}
    for r in read_jsonl(ATTEMPTS):
        if r["task_id"] in text:
            cost[(r["task_id"], r["model"])] = attempt_usd(r, cards[r["model"]], text[r["task_id"]])
    return res, text, cost


def attempt_usd(row: dict, card: dict, text: str) -> float:
    """Logged $ for OpenRouter attempts; subscription attempts (logged as $0) are priced like
    data/outcomes/REPORT_v4_attempts.md: (system + task chars)/4 input + logged output tokens x card price."""
    if row.get("cost_attempt"):
        return float(row["cost_attempt"])
    inp = (len(ATTEMPT_SYSTEM) + len(text)) / 4
    return (inp * card["cost"]["input_per_mtok"] + (row.get("out_tokens") or 0) * card["cost"]["output_per_mtok"]) / 1e6


def est_cost(card: dict, text: str, profile: TaskProfile) -> float:
    out_tok = 10.0 ** float(profile.out_tokens_log10.get("p50", 3.0))
    in_tok = estimate_input_tokens({"text": text})
    return (in_tok * card["cost"]["input_per_mtok"] + out_tok * card["cost"]["output_per_mtok"]) / 1e6


def full_tasks(res, cost, pool):
    return sorted(t for t, d in res.items() if all(c in d and (t, c) in cost for c in pool))


# ----------------------------------------------------------------------------------------------- scoring
def score(picks: dict[str, list[str]], res, cost, pool, strength) -> dict:
    """picks: task -> attempted models in order (single-shot = one). Success = any attempt passed."""
    succ, usd, under, over, n_att = [], [], [], [], []
    for t, seq in picks.items():
        ok = any(res[t][m] for m in seq)
        succ.append(ok)
        usd.append(sum(cost[(t, m)] for m in seq))
        n_att.append(len(seq))
        first = seq[0]
        # under-estimation: first pick failed while a stronger pool model passed
        under.append(not res[t][first] and any(res[t][m] and strength[m] > strength[first] for m in pool))
        # over-spend: first pick passed but a cheaper pool model also passed
        over.append(bool(res[t][first]) and any(res[t][m] and cost[(t, m)] < cost[(t, first)] for m in pool))
    return {"n": len(succ), "success": np.array(succ, float), "usd": np.array(usd), "under": np.array(under, float),
            "over": np.array(over, float), "attempts": np.array(n_att, float)}


def summary(s: dict, boot: int = 0, seed: int = 0) -> dict:
    out = {"n": s["n"], "success_per_100": round(100 * s["success"].mean(), 1),
           "usd_per_100": round(100 * s["usd"].mean(), 4), "under_est_rate": round(s["under"].mean(), 3),
           "over_spend_rate": round(s["over"].mean(), 3), "mean_attempts": round(s["attempts"].mean(), 2)}
    if boot:
        rng = np.random.default_rng(seed)
        idx = rng.integers(0, s["n"], size=(boot, s["n"]))
        for k, scale in (("success", 100), ("usd", 100), ("under", 1)):
            v = s[k][idx].mean(axis=1) * scale
            out[f"{k}_ci95"] = [round(float(np.percentile(v, 2.5)), 4), round(float(np.percentile(v, 97.5)), 4)]
    return out


# ----------------------------------------------------------------------------------------------- tuning
def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def off_matrix(esc: dict, pool: list[str]) -> np.ndarray:
    return np.array([[0.0 if a == b else esc.get(a, {}).get(b, 0.0) for b in pool] for a in pool])


def simulate(tasks, pool, PL, C, strength_arr, res, mode, prm, prior=None, PM=None):
    """Single-shot picks; PL / PM: task -> calibrated out-of-fold lower bounds / P over pool."""
    return {t: [pool[choose(mode, PL[t], C[t], np.zeros(len(pool)), strength_arr, prm["min_p"], prm["L"],
                            w_cost=prm["w_cost"], w_lat=0.0, prior=prior, eq_margin=prm["eq"],
                            p_mean=None if PM is None else PM[t])[0]]] for t in tasks}


def simulate_ladder(tasks, pool, PL, C, strength_arr, res, off, lam, attempts):
    """Follow the recommended escalation ladder until a pass (judge label) or `attempts` tries."""
    picks = {}
    for t in tasks:
        lad = ladder(PL[t], C[t], strength_arr, off, lam, allowed=free_guard(PL[t], C[t]))
        seq = []
        for i in lad[:attempts]:
            seq.append(pool[i])
            if res[t][pool[i]]:
                break
        picks[t] = seq
    return picks


def tune(args):
    res, text, cost = outcomes({"train", "val"})
    cards = load_cards()
    prof_dir = Path(args.profiler).resolve().name
    profiles = {t: TaskProfile.from_dict(p) for t, p in
                json.loads((ROOT / f"checkpoints/v4/success/profiles_{prof_dir}.json").read_text()).items()}
    oof = {(r["task_id"], r["card_id"]): r for r in read_jsonl(ROOT / f"checkpoints/v4/success/success_oof_{prof_dir}.jsonl")}
    head = json.loads((Path(args.profiler) / "success_head.json").read_text())
    esc, base_rate = head["escalation_logit"], head["base_rate"]
    all9 = sorted({c for d in res.values() for c in d})
    pools = {"9-model": all9, "8-model (no opus)": [c for c in all9 if c != "claude-opus-5.5"],
             "4 subscription": list(SUB4)}
    grid = {"L": [0.0, 0.005, 0.02, 0.05, 0.1], "min_p": [0.5, 0.6, 0.7, 0.8, 0.9],
            "w_cost": [0.0, 0.02, 0.05, 0.1, 0.3, 1.0], "eq": [-1.0, 0.0, 0.01, 0.02, 0.03, 0.05], "lam": [0.0, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0]}
    report = {"grid": grid, "pools": {}}
    for pname, pool in pools.items():
        tasks = full_tasks(res, cost, pool)
        strength = {c: card_strength(cards[c]) for c in pool}
        s_arr = np.array([strength[c] for c in pool])
        C = {t: np.array([est_cost(cards[c], text[t], profiles[t]) for c in pool]) for t in tasks}
        PL = {t: np.array([oof[(t, c)]["p_lower"] for c in pool]) for t in tasks}
        PM = {t: np.array([oof[(t, c)]["p"] for c in pool]) for t in tasks}
        base = {f"always {c}": summary(score({t: [c] for t in tasks}, res, cost, pool, strength)) for c in pool}
        base["oracle"] = summary(score({t: [min((c for c in pool if res[t][c]), key=lambda c: cost[(t, c)],
                                                 default=max(pool, key=strength.get))] for t in tasks},
                                       res, cost, pool, strength))
        rows = []
        for mode in MODES:
            for L, mp, wc, eq in itertools.product(grid["L"], grid["min_p"], grid["w_cost"], grid["eq"]):
                if (mode != "cheapest_above_threshold" and mp != grid["min_p"][0]) or \
                        (mode != "max_utility" and wc != grid["w_cost"][0]):
                    continue
                prm = {"L": L, "min_p": mp, "w_cost": wc, "eq": eq}
                one = summary(score(simulate(tasks, pool, PL, C, s_arr, res, mode, prm,
                                             prior=np.array([base_rate[c] for c in pool]), PM=PM), res, cost, pool,
                                    strength))
                rows.append({"mode": mode, **prm, "single": one})
        off = off_matrix(esc, pool)
        lad = [{"lam": lam, **{f"within{k}": summary(score(simulate_ladder(tasks, pool, PL, C, s_arr, res, off, lam, k),
                                                           res, cost, pool, strength)) for k in (1, 2, 3)}}
               for lam in grid["lam"]]
        report["pools"][pname] = {"n_tasks": len(tasks), "baselines": base, "grid": rows, "ladder": lad}
        print(f"{pname}: {len(tasks)} tasks; oracle {base['oracle']['success_per_100']}", flush=True)
    report["selection"] = select(report["pools"]["8-model (no opus)"])
    print("selected:", report["selection"], flush=True)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=1))


EQ_MARGIN = 0.05


def select(pool_report: dict) -> dict:
    """Pre-registered rules (8-model train/val pool, out-of-fold calibrated lower bounds):
    single-shot - maximise success with $ <= the best single model's $; ties (1-point buckets) -> lower
    under-estimation -> lower $. Shared (L, eq_margin) = best summed success over the 3 modes (1-point buckets),
    then lower summed $.
    ladder - maximise success within 2 attempts with $ <= the best single model's $; ties -> lower $."""
    base = pool_report["baselines"]
    best_single = max((v for k, v in base.items() if k.startswith("always ")), key=lambda v: v["success_per_100"])
    cap = best_single["usd_per_100"]

    def best(rows):
        ok = [r for r in rows if r["single"]["usd_per_100"] <= cap] or rows
        return max(ok, key=lambda r: (round(r["single"]["success_per_100"]), -r["single"]["under_est_rate"],
                                      -r["single"]["usd_per_100"]))
    # requirement (architect review): roughly equal P -> the cheaper card; eq_margin fixed at 0.05 (~ the head's uncertainty), not tuned
    grid = [r for r in pool_report["grid"] if r["eq"] == EQ_MARGIN]

    def shared_key(k):
        rows_k = [r for r in grid if (r["L"], r["eq"]) == k]
        bs = [best([r for r in rows_k if r["mode"] == m])["single"] for m in MODES]
        return (round(sum(b["success_per_100"] for b in bs)), -sum(b["usd_per_100"] for b in bs))
    L, eq = max({(r["L"], r["eq"]) for r in grid}, key=shared_key)
    rows = [r for r in grid if (r["L"], r["eq"]) == (L, eq)]
    ch = best([r for r in rows if r["mode"] == "cheapest_above_threshold"])
    mu = best([r for r in rows if r["mode"] == "max_utility"])
    lad_ok = [r for r in pool_report["ladder"] if r["within2"]["usd_per_100"] <= cap] or pool_report["ladder"]
    lad = max(lad_ok, key=lambda r: (r["within2"]["success_per_100"], -r["within2"]["usd_per_100"]))
    return {"failure_penalty_usd": L, "equal_p_margin": eq, "min_p_success": ch["min_p"], "w_cost": mu["w_cost"], "ladder_lambda": lad["lam"],
            "best_single_usd_cap": cap, "rule": select.__doc__.strip()}


# ----------------------------------------------------------------------------------------------- gold
CHEAP_PRICE = 1.0  # $/Mtok in+out: luna, haiku, qwen3.8-flash, minimax-m3.1-flash


def run_router(matcher, profiler, tasks, text, res, pool, mode, retries):
    """Real Matcher.route / .escalate loop; the judge label is the failure signal."""
    picks = {}
    for t in tasks:
        req = {"task": {"text": text[t]}, "pool": list(pool), "preferences": {"mode": mode},
               "return_top_k": len(pool)}
        prof = profiler.profile({"text": text[t], "context": {}})
        resp = matcher.route(req, prof, trace_id="v4-eval")
        seq = []
        for k in range(retries + 1):
            m = resp["choice"]["model_id"]
            if m is None:
                break
            seq.append(m)
            if res[t][m] or k == retries or len(seq) == len(pool):
                break
            resp = matcher.escalate(req, prof, resp, m, trace_id="v4-eval")
        picks[t] = seq
    return picks


def run_ladder(matcher, profiler, tasks, text, res, pool, attempts):
    """Follow the response's escalation_ladder from the start (judge label = failure signal)."""
    picks = {}
    for t in tasks:
        req = {"task": {"text": text[t]}, "pool": list(pool), "return_top_k": len(pool)}
        resp = matcher.route(req, profiler.profile({"text": text[t], "context": {}}), trace_id="v4-eval")
        seq = []
        for r in resp["escalation_ladder"][:attempts]:
            seq.append(r["model_id"])
            if res[t][r["model_id"]]:
                break
        picks[t] = seq
    return picks


def gold_calibration(matcher, profiler, tasks, text, res, pool, key) -> dict:
    """ECE / mean / AUC of a displayed P (`key`) against gold pass labels over every (task, card) cell."""
    from sklearn.metrics import roc_auc_score
    P, Y = [], []
    for t in tasks:
        r = matcher.route({"task": {"text": text[t]}, "pool": list(pool), "return_top_k": len(pool)},
                          profiler.profile({"text": text[t], "context": {}}), trace_id="v4-eval")
        for x in r["ranking"]:
            P.append(x[key])
            Y.append(res[t][x["model_id"]])
    P, Y = np.array(P), np.array(Y)
    b = np.minimum((P * 10).astype(int), 9)
    ece = sum(abs(P[b == k].mean() - Y[b == k].mean()) * (b == k).mean() for k in range(10) if (b == k).any())
    return {"n_cells": len(P), "ece": round(float(ece), 4), "mean_p": round(float(P.mean()), 4),
            "pass_rate": round(float(Y.mean()), 4), "auc": round(float(roc_auc_score(Y, P)), 4)}


def free_pick_rate(matcher, profiler, texts, mode) -> dict:
    """Full default card pool (no outcomes for most cards): how often a $0 / local card is picked."""
    cards = load_cards()
    n_free, n = 0, 0
    for t in texts:
        r = matcher.route({"task": {"text": t}, "preferences": {"mode": mode}},
                          profiler.profile({"text": t, "context": {}}), trace_id="v4-eval")
        m = r["choice"]["model_id"]
        c = cards[m]["cost"]
        n_free += (c["input_per_mtok"] + c["output_per_mtok"]) == 0
        n += 1
    return {"n": n, "free_pick_rate": round(n_free / n, 3)}


def gold(args):
    from panda_router.matcher import Matcher
    from panda_router.model.onnx_profiler import OnnxProfiler

    res, text, cost = outcomes({"gold"})
    cards = load_cards()
    all9 = sorted({c for d in res.values() for c in d})
    v4p, v3p = OnnxProfiler(args.profiler), OnnxProfiler(str(ROOT / "artifacts/panda-router-v3"))
    routers = {"v4": (Matcher(), v4p), "v3": (Matcher(policy="v3", success_head=None, calibration=False), v3p)}
    out = {"pools": {}, "boot": args.boot}
    for pname, pool in (("9-model", all9), ("4 subscription", list(SUB4))):
        tasks = full_tasks(res, cost, pool)
        strength = {c: card_strength(cards[c]) for c in pool}
        cheap = {c for c in pool if card_price(cards[c]) <= CHEAP_PRICE}
        rows = {}

        def add(name, picks):
            sm = summary(score(picks, res, cost, pool, strength), boot=args.boot)
            firsts = [seq[0] for seq in picks.values()]
            ch = [t for t, seq in picks.items() if seq[0] in cheap]
            sm["cheap_pick_rate"] = round(len(ch) / len(picks), 3)
            sm["cheap_pick_fail_rate"] = round(float(np.mean([not res[t][picks[t][0]] for t in ch])), 3) if ch else None
            sm["picks"] = {m: firsts.count(m) for m in sorted(set(firsts))}
            rows[name] = sm
            print(f"  {pname} {name}: {sm['success_per_100']} {sm.get('success_ci95')} ${sm['usd_per_100']}", flush=True)

        for c in pool:
            add(f"always {c}", {t: [c] for t in tasks})
        add("always-cheapest (card price)", {t: [min(pool, key=lambda c: (card_price(cards[c]), c))] for t in tasks})
        add("always-strongest (card skills)", {t: [max(pool, key=strength.get)] for t in tasks})
        add("oracle (cheapest passing)", {t: [min((c for c in pool if res[t][c]), key=lambda c: cost[(t, c)],
                                                  default=max(pool, key=strength.get))] for t in tasks})
        for rname, (mt, pr) in routers.items():
            for mode in MODES:
                for k in ((0, 1, 2) if rname == "v3" or mode == "max_utility" else (0,)):
                    label = f"{rname} {mode}" + (f" cascade<= {k + 1} attempts" if k else " single-shot")
                    add(label, run_router(mt, pr, tasks, text, res, pool, mode, k))
        v4m, v4pr = routers["v4"]
        for k in (1, 2, 3):
            add(f"v4 escalation_ladder within {k}", run_ladder(v4m, v4pr, tasks, text, res, pool, k))
        cal = {"v4.1 p_success (calibrated)": gold_calibration(v4m, v4pr, tasks, text, res, pool, "p_success"),
               "v4.1 p_success_lower": gold_calibration(v4m, v4pr, tasks, text, res, pool, "p_success_lower")}
        if args.old_head:
            old = Matcher(success_head=args.old_head)
            cal["v4.0 p_success (fail-weight 2.5 + LCB)"] = gold_calibration(old, v4pr, tasks, text, res, pool,
                                                                             "p_success_lower")
        out["pools"][pname] = {"n_tasks": len(tasks), "cheap_models": sorted(cheap), "rows": rows, "calibration": cal}
        print(json.dumps(cal), flush=True)
    texts = [text[t] for t in sorted(text)]
    out["free_picks_full_pool"] = {f"{r} {m}": free_pick_rate(mt, pr, texts, m)
                                   for r, (mt, pr) in routers.items() for m in MODES}
    print(json.dumps(out["free_picks_full_pool"]), flush=True)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["tune", "gold"])
    ap.add_argument("--profiler", default=str(ROOT / "artifacts/panda-router-v4"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--old-head", default=None, help="v4.0 success head json for the before/after calibration table")
    args = ap.parse_args()
    (tune if args.cmd == "tune" else gold)(args)


if __name__ == "__main__":
    main()
