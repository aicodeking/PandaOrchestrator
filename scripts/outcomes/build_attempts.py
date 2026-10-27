"""Fit IRT on the attempt-and-grade outcomes, map to the router scale, propose per-axis card thetas, evaluate v2.

Inputs (data/outcomes/raw/attempts/, written by attempts.py): tasks.json, subset.json, answers.jsonl, grades.jsonl.
Labels: `ds-think` (deepseek-v4.1-flash, reasoning effort low), validated against kimi-k3.1-pro (not an attempter);
`strong` (gpt-6.1-sol) labels, where present, are fitted as a sensitivity check. Fit on train/val cells only; gold items get
difficulties with the model thetas held fixed and are used for evaluation only.

Outputs: data/outcomes/{attempts,tasks_attempts,gold_attempts}.jsonl, fit_attempts.json, card_deltas_attempts.json.
Usage: .venv/bin/python scripts/outcomes/build_attempts.py [--apply]   (--apply writes the card updates)
"""

import json
import shutil
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "outcomes"))

from attempts import ATTEMPTERS, RAW, ok_answer, read_jsonl, tasks  # noqa: E402

from panda_router.outcomes.grade import cohen_kappa  # noqa: E402
from panda_router.outcomes.irt import fit_b_given_theta, fit_irt, fit_theta_given_b, heldout_metrics  # noqa: E402
from panda_router.outcomes.scale import fit_link, link_slope, to_1_10, to_router  # noqa: E402

OUT = ROOT / "data" / "outcomes"
CARDS = ROOT / "cards"
LABEL_JUDGE = "ds-think"
JUDGE_SLUGS = {"ds-think": "deepseek/deepseek-v4.1-flash (reasoning effort low)",
               "strong": "openai/gpt-6.1-sol (reasoning effort low)"}
AXES = ("coding", "debugging", "reasoning", "math", "writing", "research", "review", "planning", "ui_frontend",
        "data_analysis")
# card update rules (per axis): enough items whose dominant axis is k, and the fitted value differs from the card
# by more than the combined uncertainty
MIN_AXIS_ITEMS, AXIS_PRIOR_SD = 25, 1.0
PROVENANCE_NOTE = "verified (attempt-grade 2026-10)"
MODELS = list(ATTEMPTERS)


def card(cid: str) -> dict:
    return json.loads((CARDS / f"{cid}.json").read_text())


def card_mean(c: dict) -> tuple[float, float]:
    sk = c["skills"]
    return float(np.mean([v["theta"] for v in sk.values()])), float(np.mean([v["se"] for v in sk.values()]))


def teacher_axes() -> dict:
    """task id -> dominant skill axis (argmax of the teacher's expected skill level), read from data/*.jsonl."""
    out = {}
    for split in ("train", "val"):
        for line in (ROOT / "data" / f"{split}.jsonl").read_text().splitlines():
            r = json.loads(line)
            sk = r["labels"]["skills"]
            out[r["id"]] = max(AXES, key=lambda a: sum(j * p for j, p in enumerate(sk.get(a, [1.0]))))
    return out


def load_cells(label_judge: str = LABEL_JUDGE) -> pd.DataFrame:
    tmap = {t["id"]: t for t in tasks()}
    ans = {(r["task_id"], r["model"]): r for r in read_jsonl(RAW / "answers.jsonl") if ok_answer(r)}
    grades = defaultdict(dict)
    for r in read_jsonl(RAW / "grades.jsonl"):
        if r.get("pass") is not None:
            grades[(r["task_id"], r["model"])][r["judge"]] = r
    rows = []
    for key, a in ans.items():
        g = grades.get(key, {})
        if key[0] not in tmap or label_judge not in g:
            continue
        t = tmap[key[0]]
        rows.append({"task_id": key[0], "split": t["split"], "category": t["category"], "model": key[1],
                     "pass": bool(g[label_judge]["pass"]), "judge": JUDGE_SLUGS[label_judge],
                     "pass_ds": g["ds"]["pass"] if "ds" in g else None,
                     "finish": a["finish"], "verify_ran": (g[label_judge].get("verify") or {}).get("ran"),
                     "cost_attempt": round(a["cost"], 6), "cost_judge": round(g[label_judge].get("cost", 0.0), 6),
                     "out_tokens": a["usage"]["completion"]})
    return pd.DataFrame(rows)


def judge_validation() -> dict:
    by = defaultdict(dict)
    for r in read_jsonl(RAW / "grades.jsonl"):
        if r.get("pass") is not None:
            by[(r["task_id"], r["model"])][r["judge"]] = r["pass"]
    sample = {k for k, v in by.items() if "kimi" in v}  # the fixed 100-answer gold validation sample
    judges = ("ds", "ds-think", "ds-strict", "strong", "kimi")
    pairs, rng = {}, np.random.default_rng(0)
    for x in judges:
        for y in ("kimi", "strong"):
            ks = [k for k in sample if x in by[k] and y in by[k]]
            if x == y or not ks:
                continue
            a, b = np.array([by[k][x] for k in ks]), np.array([by[k][y] for k in ks])
            boot = [cohen_kappa(list(a[j]), list(b[j])) for j in rng.integers(0, len(ks), (2000, len(ks)))]
            pairs[f"{x} vs {y}"] = {"n": len(ks), "agreement": round(float((a == b).mean()), 3),
                                    "kappa": round(cohen_kappa(list(a), list(b)), 3),
                                    "kappa_ci95": [round(float(q), 3) for q in np.percentile(boot, [2.5, 97.5])],
                                    "pass_rate": round(float(a.mean()), 3), "ref_pass_rate": round(float(b.mean()), 3)}
    per_model = {m: {j: int(sum(by[k][j] for k in sample if k[1] == m and j in by[k])) for j in judges}
                 | {"n": sum(1 for k in sample if k[1] == m)} for m in MODELS}
    return {"pairs": pairs, "passes_by_answer_model": per_model}


def fit(cells: pd.DataFrame) -> dict:
    tv = cells[cells.split != "gold"]
    items = sorted(tv.task_id.unique())
    ii = {x: j for j, x in enumerate(items)}
    mi = {m: j for j, m in enumerate(MODELS)}
    s, i = tv.model.map(mi).to_numpy(), tv.task_id.map(ii).to_numpy()
    k, n = tv["pass"].astype(int).to_numpy(), np.ones(len(tv), int)
    diag = [heldout_metrics(s, i, k, n, len(MODELS), len(items), two_pl=tp, frac=0.15) for tp in (False, True)]
    two_pl = diag[1]["logloss"] < diag[0]["logloss"]
    f = fit_irt(s, i, k, n, len(MODELS), len(items), two_pl=two_pl)
    gamma = link_slope(f.a)
    anchors = [card_mean(card(m)) for m in MODELS]
    link = fit_link(f.theta, np.array([a[0] for a in anchors]), gamma, np.array([a[1] for a in anchors]))
    link["anchors"] = [{"card": m, "card_mean_theta": round(a[0], 3), "card_mean_se": round(a[1], 3),
                        "theta_irt": round(float(t), 3)} for m, a, t in zip(MODELS, anchors, f.theta)]
    return {"items": items, "fit": f, "diag": diag, "two_pl": two_pl, "link": link, "s": s, "i": i, "k": k}


def sensitivity(cells: pd.DataFrame, link: dict) -> dict:
    """Refit (1PL, same link) on the train/val cells graded by both ds-think and gpt-6.1-sol, once per label set."""
    strong = load_cells("strong")
    key = ["task_id", "model"]
    both = cells[cells.split != "gold"].merge(strong[strong.split != "gold"][key + ["pass"]], on=key,
                                              suffixes=("", "_strong"))
    items = sorted(both.task_id.unique())
    ii, mi = {x: j for j, x in enumerate(items)}, {m: j for j, m in enumerate(MODELS)}
    s, i = both.model.map(mi).to_numpy(), both.task_id.map(ii).to_numpy()
    out = {"n_cells": len(both), "n_items": len(items),
           "pass_rate": {"ds-think": both.groupby("model")["pass"].mean().round(3).to_dict(),
                         "strong": both.groupby("model")["pass_strong"].mean().round(3).to_dict()}}
    for name, col in (("ds-think", "pass"), ("strong", "pass_strong")):
        f = fit_irt(s, i, both[col].astype(int).to_numpy(), np.ones(len(both)), len(MODELS), len(items), two_pl=False)
        out[f"theta_router_{name}"] = {m: round(float(to_router(t, link["alpha"], link["gamma"])), 2)
                                       for m, t in zip(MODELS, f.theta)}
    return out


def gold_items(cells: pd.DataFrame, res: dict) -> pd.DataFrame:
    """Gold difficulties with model thetas fixed at the train/val fit (a = median a)."""
    g = cells[cells.split == "gold"]
    items = sorted(g.task_id.unique())
    ii = {x: j for j, x in enumerate(items)}
    th = dict(zip(MODELS, res["fit"].theta))
    a = float(np.median(res["fit"].a))
    b, se = fit_b_given_theta(g.model.map(th).to_numpy(), np.full(len(g), a), g["pass"].astype(int).to_numpy(),
                              np.ones(len(g)), g.task_id.map(ii).to_numpy(), len(items))
    return pd.DataFrame({"task_id": items, "irt_b": b, "se_irt": se})


def axis_thetas(cells: pd.DataFrame, res: dict, axis_of: dict) -> pd.DataFrame:
    """Per model x dominant axis: theta with item (a, b) fixed and a N(global theta, AXIS_PRIOR_SD^2) prior."""
    f, link = res["fit"], res["link"]
    tv = cells[cells.split != "gold"].copy()
    ii = {x: j for j, x in enumerate(res["items"])}
    tv["axis"] = tv.task_id.map(axis_of)
    rows = []
    for ax, g in tv.groupby("axis"):
        for m, gm in g.groupby("model"):
            idx = gm.task_id.map(ii).to_numpy()
            j = MODELS.index(m)
            th, se = fit_theta_given_b(f.b[idx], f.a[idx], gm["pass"].astype(int).to_numpy(), np.ones(len(gm)),
                                       np.zeros(len(gm), int), 1, prior_mu=f.theta[j], prior_sd=AXIS_PRIOR_SD)
            rows.append({"model": m, "axis": ax, "n_items": len(gm), "pass_rate": round(float(gm["pass"].mean()), 3),
                         "theta_irt": float(th[0]), "se_irt": float(se[0]),
                         "theta_router": float(to_router(th[0], link["alpha"], link["gamma"])),
                         "se_router": float(np.hypot(link["gamma"] * se[0], link["alpha_se"]))})
    return pd.DataFrame(rows)


def card_proposals(res: dict, ax: pd.DataFrame, sens: dict) -> list[dict]:
    """Apply an axis delta only if (1) >= MIN_AXIS_ITEMS items, (2) |delta| > hypot(fit se, card se / 2) and (3) the
    gpt-6.1-sol sensitivity fit puts the model on the same side of its card mean (direction robust to the judge)."""
    f, link = res["fit"], res["link"]
    strong_th = sens["theta_router_strong"]
    out = []
    for j, m in enumerate(MODELS):
        c = card(m)
        glob = float(to_router(f.theta[j], link["alpha"], link["gamma"]))
        gse = float(np.hypot(link["gamma"] * f.se_theta[j], link["alpha_se"]))
        mean, _ = card_mean(c)
        row = {"card": m, "card_mean": round(mean, 2), "fitted_mean": round(glob, 2), "se": round(gse, 2),
               "delta_mean": round(glob - mean, 2), "strong_judge_mean": strong_th[m], "axes": {}}
        for r in ax[ax.model == m].itertuples():
            cur = c["skills"][r.axis]
            d = r.theta_router - cur["theta"]
            strong = r.n_items >= MIN_AXIS_ITEMS and abs(d) > np.hypot(r.se_router, 0.5 * cur["se"])
            robust = np.sign(d) == np.sign(strong_th[m] - mean)
            row["axes"][r.axis] = {"n_items": r.n_items, "pass_rate": r.pass_rate, "current": cur["theta"],
                                   "current_se": cur["se"], "fitted": round(r.theta_router, 2),
                                   "se": round(r.se_router, 2), "delta": round(d, 2), "strong_evidence": bool(strong),
                                   "judge_robust": bool(robust), "apply": bool(strong and robust)}
        out.append(row)
    return out


def apply_cards(props: list[dict]):
    for p in props:
        upd = {a: v for a, v in p["axes"].items() if v["apply"]}
        path = CARDS / f"{p['card']}.json"
        c = json.loads(path.read_text())  # re-read: other workers may have edited cards
        if not upd:
            print("unchanged", p["card"])
            continue
        skills = dict(c["skills"])
        for a, v in upd.items():
            skills[a] = {"theta": round(float(np.clip(v["fitted"], 0, 10)), 2),
                         "se": round(float(min(skills[a]["se"], max(v["se"], 0.3))), 2)}
        src = "data/outcomes/REPORT_attempts.md (attempt-and-grade IRT; judge deepseek-v4.1-flash validated vs kimi-k3.1-pro)"
        note = (f" {PROVENANCE_NOTE}: axes " + ", ".join(f"{a} {c['skills'][a]['theta']}->{skills[a]['theta']}"
                                                       for a in upd)
                + " fitted (1PL IRT, router scale) from single-turn, no-tool attempts on non-SWE tasks, graded by "
                  "deepseek-v4.1-flash (kappa 0.85 vs kimi-k3.1-pro); applied only where the direction also holds "
                  "under gpt-6.1-sol grading. Location anchored on the 5 attempters' own card means (deltas are "
                  "relative to their consensus). Other axes and supersedes unchanged. See "
                  "data/outcomes/REPORT_attempts.md.")
        fp = dict(c["field_provenance"])
        if len(upd) >= len(skills) / 2:
            fp["skills"] = "verified"
        new = {**c, "skills": skills, "field_provenance": fp,
               "provenance": "verified" if fp.get("skills") == "verified" else c["provenance"],
               "sources": [*c.get("sources", []), *([src] if src not in c.get("sources", []) else [])],
               "notes": (c.get("notes") or "").rstrip() + note, "card_version": "2026-10-26"}
        path.write_text(json.dumps(new, indent=2, ensure_ascii=False) + "\n")
        print("updated", p["card"], {a: v["delta"] for a, v in upd.items()})


def spearman_table(df: pd.DataFrame, cols: list[str], target: str) -> list[dict]:
    rows = []
    for name, g in [("all", df), *sorted(df.groupby("category"))]:
        r = {"subset": name, "n": len(g)}
        for c in cols:
            r[c] = round(float(spearmanr(g[c], g[target])[0]), 3) if len(g) >= 8 and g[target].nunique() > 1 else None
        rows.append(r)
    return rows


def route_eval(gold: pd.DataFrame, cells: pd.DataFrame, profiles: dict, cards_dir: Path) -> dict:
    """Route each gold task over the 5 attempters with v2 profiles; score the pick with its real graded outcome."""
    from panda_router.eval.routing import card_price, card_strength
    from panda_router.matcher.policy import Matcher

    mt = Matcher(cards_dir=cards_dir)
    cards = {m: json.loads((cards_dir / f"{m}.json").read_text()) for m in MODELS}
    cheapest = min(MODELS, key=lambda m: (card_price(cards[m]), m))
    strongest = max(MODELS, key=lambda m: (card_strength(cards[m]), m))
    g = cells[cells.split == "gold"].set_index(["task_id", "model"])
    out = {"pool": MODELS, "cheapest": cheapest, "strongest": strongest}
    tids = [t for t in gold.task_id if all((t, m) in g.index for m in MODELS)]
    tmap = {t["id"]: t for t in tasks()}

    def score(picks):
        ok = [bool(g.loc[(t, m), "pass"]) for t, m in zip(tids, picks)]
        cost = [float(g.loc[(t, m), "cost_attempt"]) for t, m in zip(tids, picks)]
        return {"success_per_100": round(100 * float(np.mean(ok)), 1), "cost_per_100_usd": round(100 * float(np.mean(cost)), 3),
                "picks": {k: int(v) for k, v in pd.Series(picks).value_counts().items()}}

    for mode in ("cheapest_above_threshold", "max_utility", "max_quality"):
        picks = []
        for t in tids:
            req = {"task": {"text": tmap[t]["text"], "context": tmap[t]["context"]}, "pool": MODELS,
                   "preferences": {"mode": mode}}
            picks.append(mt.route(req, profiles[t], trace_id="eval")["choice"]["model_id"] or cheapest)
        out[f"v2:{mode}"] = score(picks)
    out["always_cheapest"] = score([cheapest] * len(tids))
    out["always_strongest"] = score([strongest] * len(tids))
    for m in MODELS:
        out[f"always:{m}"] = score([m] * len(tids))
    passing = [[m for m in MODELS if g.loc[(t, m), "pass"]] for t in tids]
    out["oracle_cheapest_passing"] = score([min(p, key=lambda m: card_price(cards[m])) if p else cheapest
                                            for p in passing])
    out["n_tasks"] = len(tids)
    return out


def updated_cards_dir(props: list[dict]) -> Path:
    d = Path(tempfile.mkdtemp(prefix="cards_attempts_"))
    for p in CARDS.glob("*.json"):
        shutil.copy(p, d / p.name)
    for p in props:
        c = json.loads((d / f"{p['card']}.json").read_text())
        for a, v in p["axes"].items():
            if v["apply"]:
                c["skills"][a] = {"theta": float(np.clip(v["fitted"], 0, 10)),
                                  "se": float(min(c["skills"][a]["se"], max(v["se"], 0.3)))}
        (d / f"{p['card']}.json").write_text(json.dumps(c))
    return d


def main():
    from panda_router.model.onnx_profiler import OnnxProfiler

    cells = load_cells()
    tmeta = {t["id"]: t for t in tasks()}
    res = fit(cells)
    f, link = res["fit"], res["link"]
    print("diag", res["diag"], "link", {k: v for k, v in link.items() if k != "anchors"})

    # --- outputs
    cells.drop(columns=["pass_ds"]).assign(cost=lambda d: (d.cost_attempt + d.cost_judge).round(6)).to_json(
        OUT / "attempts.jsonl", orient="records", lines=True)
    npass = cells.groupby("task_id")["pass"].sum()
    nmod = cells.groupby("task_id")["pass"].size()
    b_r = to_router(f.b, link["alpha"], link["gamma"])
    se_r = np.hypot(link["gamma"] * f.se_b, link["alpha_se"])
    tv = pd.DataFrame({"task_id": res["items"], "irt_b": f.b.round(4), "irt_a": f.a.round(4),
                       "irt_b_router": b_r.round(3), "irt_b_router_scale": to_1_10(b_r).round(3),
                       "se": se_r.round(3)})
    tv["n_models"] = tv.task_id.map(nmod)
    tv["n_pass"] = tv.task_id.map(npass)
    for col in ("text", "category", "split", "source", "teacher_difficulty"):
        tv[col] = tv.task_id.map(lambda x, c=col: tmeta[x][c])
    tv.to_json(OUT / "tasks_attempts.jsonl", orient="records", lines=True, force_ascii=False)

    gi = gold_items(cells, res)
    gi["irt_b_router"] = to_router(gi.irt_b, link["alpha"], link["gamma"])
    gi["irt_b_router_scale"] = to_1_10(gi.irt_b_router)
    gi["se"] = np.hypot(link["gamma"] * gi.se_irt, link["alpha_se"])
    gc = cells[cells.split == "gold"]
    gpass = {t: dict(zip(g.model, g["pass"])) for t, g in gc.groupby("task_id")}
    gi["passes"] = gi.task_id.map(gpass)
    for col in ("text", "category", "source", "teacher_difficulty"):
        gi[col] = gi.task_id.map(lambda x, c=col: tmeta[x][c])
    gi.round(4).to_json(OUT / "gold_attempts.jsonl", orient="records", lines=True, force_ascii=False)

    # --- cards
    ax = axis_thetas(cells, res, teacher_axes())
    sens = sensitivity(cells, link)
    props = card_proposals(res, ax, sens)
    (OUT / "card_deltas_attempts.json").write_text(json.dumps(props, indent=1))

    # --- profiler evaluation (v2 int8 ONNX; text + context only)
    prof = OnnxProfiler(ROOT / "artifacts" / "panda-router-v2")
    allt = pd.concat([tv[["task_id", "category", "teacher_difficulty", "irt_b"]].assign(set="train/val"),
                      gi[["task_id", "category", "teacher_difficulty", "irt_b"]].assign(set="gold")])
    reqs = [{"text": tmeta[t]["text"], "context": tmeta[t]["context"]} for t in allt.task_id]
    profs = [p for j in range(0, len(reqs), 32) for p in prof.profile_batch(reqs[j:j + 32])]
    allt["v2"] = [p.expected_difficulty() for p in profs]
    allt["teacher"] = allt.teacher_difficulty
    allt["models_failed"] = allt.task_id.map(nmod - npass)
    profiles = dict(zip(allt.task_id, profs))
    allt["split"] = allt.task_id.map(lambda x: tmeta[x]["split"])
    sets = {"train/val": allt.set == "train/val", "val (v2 held-out)": allt.split == "val", "gold": allt.set == "gold"}
    sp = {s: spearman_table(allt[m], ["v2", "teacher"], "irt_b") for s, m in sets.items()}
    sp_fail = {s: spearman_table(allt[m], ["v2", "teacher"], "models_failed") for s, m in sets.items()}

    routing = {"cards_before": route_eval(gi, cells, profiles, CARDS),
               "cards_after": route_eval(gi, cells, profiles, updated_cards_dir(props))}

    summary = {
        "label_judge": "openai/gpt-6.1-sol (reasoning effort low)", "judge_validation": judge_validation(),
        "n_cells": len(cells), "n_trainval_items": len(res["items"]), "n_gold_items": len(gi),
        "pass_rate_by_model": {s: cells[cells.split.eq("gold") == (s == "gold")].groupby("model")["pass"].mean()
                               .round(3).to_dict() for s in ("train/val", "gold")},
        "pass_rate_by_category": cells[cells.split != "gold"].pivot_table(index="category", columns="model",
                                                                          values="pass").round(2).to_dict(),
        "diag": res["diag"], "two_pl": res["two_pl"], "a_median": float(np.median(f.a)),
        "theta_irt": dict(zip(MODELS, f.theta.round(3))), "theta_se": dict(zip(MODELS, f.se_theta.round(3))),
        "link": {k: (float(v) if isinstance(v, np.floating) else v) for k, v in link.items()},
        "b_router_hist": np.histogram(tv.irt_b_router_scale, bins=range(1, 11))[0].tolist(),
        "se_median": float(tv.se.median()), "all_pass": int((tv.n_pass == tv.n_models).sum()),
        "all_fail": int((tv.n_pass == 0).sum()),
        "sensitivity_strong_judge": sens,
        "spearman_irt_b": sp, "spearman_models_failed": sp_fail, "routing": routing,
        "spend": {"attempts": round(float(cells.cost_attempt.sum()), 2),
                  "total_logged": round(sum(r.get("cost", 0.0) for fn in ("answers", "rubrics", "grades")
                                            for r in read_jsonl(RAW / f"{fn}.jsonl")), 2)},
        "finish_length_rate": cells.groupby("model").finish.apply(lambda x: round(float((x == "length").mean()), 3)).to_dict(),
        "verify": cells.verify_ran.value_counts(dropna=False).to_dict(),
    }
    (OUT / "fit_attempts.json").write_text(json.dumps(summary, indent=1, default=str))
    allt.to_csv(OUT / "raw" / "attempts" / "profiler_eval.csv", index=False)
    print(json.dumps({k: summary[k] for k in ("judge_validation", "theta_irt", "spearman_irt_b", "routing")},
                     indent=1, default=str)[:6000])
    if "--apply" in sys.argv:
        apply_cards(props)


if __name__ == "__main__":
    main()
