"""Fit outcome IRT, link it to the card scale, write data/outcomes/{tasks,systems}.jsonl and fit.json.

Components (they share neither tasks nor systems, so each gets its own fit and link):
  A  swe-bench/experiments: verified + lite + full test (linked through shared instances) and multilingual
     (linked through the same mini-swe-agent v2 runs of the same model on verified). Multimodal shares no
     system or task with the rest and is left out.
  B  rebench07 (17 systems x 5 runs x 111 tasks; licence 'other' -> systems/cards only, no task rows).

Usage: .venv/bin/python scripts/outcomes/build.py [--no-eval]
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from panda_router.outcomes.irt import fit_irt, heldout_metrics  # noqa: E402
from panda_router.outcomes.load import LICENCES, load_rebench07, load_swebench, norm_text, split_tasks  # noqa: E402
from panda_router.outcomes.scale import EXACT, PREDECESSOR, fit_link, link_slope, norm_model, to_1_10, to_router  # noqa: E402

OUT = ROOT / "data" / "outcomes"
NOT_BASE = ("entropo", "swerl", "skywork", "frog", "deepswe", "mcts")  # fine-tunes: not the card's base model
MIN_N_ITEMS = 100


def card_theta(card_id: str) -> tuple[float, float]:
    c = json.loads((ROOT / "cards" / f"{card_id}.json").read_text())
    return c["skills"]["coding"]["theta"], c["skills"]["coding"]["se"]


def link_multilingual(out: pd.DataFrame, sysdf: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rename each multilingual mini-swe-agent v2 system to the verified mini v2 system of the same model."""
    sysdf = sysdf.assign(norm=sysdf.base_model_raw.map(norm_model))
    ver = sysdf[(sysdf.source == "swebench-verified") & sysdf.dir.str.contains("_mini-v2")]
    rename = {}
    for r in sysdf[sysdf.source == "swebench-multilingual"].itertuples():
        cand = ver[ver.norm == r.norm].system.tolist()
        if r.norm and "_mini-v2" in r.dir and len(cand) == 1:
            rename[r.system] = cand[0]
    out = out.assign(system=out.system.replace(rename))
    sysdf = sysdf[~sysdf.system.isin(rename)]
    return out, sysdf, rename


def fit_component(out: pd.DataFrame, name: str) -> dict:
    systems = sorted(out.system.unique())
    items = sorted(out.instance_id.unique())
    si = {x: j for j, x in enumerate(systems)}
    ii = {x: j for j, x in enumerate(items)}
    s, i = out.system.map(si).to_numpy(), out.instance_id.map(ii).to_numpy()
    k, n = out.k.to_numpy(), out.n.to_numpy()
    diag = [heldout_metrics(s, i, k, n, len(systems), len(items), two_pl=tp) for tp in (False, True)]
    two_pl = diag[1]["logloss"] < diag[0]["logloss"]
    fit = fit_irt(s, i, k, n, len(systems), len(items), two_pl=two_pl)
    print(name, diag, "->", "2PL" if two_pl else "1PL", flush=True)
    n_sys_item = np.bincount(i, minlength=len(items))
    return {"systems": systems, "items": items, "fit": fit, "diag": diag, "n_sys_item": n_sys_item,
            "trials": int(n.sum()), "cells": len(out)}


def link_component(comp: dict, sysdf: pd.DataFrame) -> dict:
    fit = comp["fit"]
    th = dict(zip(comp["systems"], fit.theta))
    anchors = []
    for r in sysdf.itertuples():
        card = EXACT.get(r.norm)
        if card and r.system in th and not any(t in r.system.lower() for t in NOT_BASE) and r.kind != "agentic_system":
            anchors.append((r.system, card, th[r.system], *card_theta(card)))
    gamma = link_slope(fit.a)
    link = fit_link(np.array([a[2] for a in anchors]), np.array([a[3] for a in anchors]), gamma,
                    np.array([a[4] for a in anchors]))
    link["anchors"] = [{"system": a[0], "card": a[1], "theta_irt": round(float(a[2]), 3), "card_theta": a[3],
                        "card_se": a[4]}
                       for a in anchors]
    return link


def systems_rows(comp, sysdf, link, src):
    fit = comp["fit"]
    by = sysdf.set_index("system")
    rows = []
    for j, x in enumerate(comp["systems"]):
        r = by.loc[x]
        rows.append({"system": x, "component": src, "source": r.source, "base_model_raw": r.base_model_raw,
                     "base_model": r.norm, "agent": r.agent, "kind": r.kind,
                     "theta_irt": round(float(fit.theta[j]), 4), "se_irt": round(float(fit.se_theta[j]), 4),
                     "theta_router": round(float(to_router(fit.theta[j], link["alpha"], link["gamma"])), 3),
                     "se_router": round(float(np.hypot(link["gamma"] * fit.se_theta[j], link["alpha_se"])), 3),
                     "exact_card": EXACT.get(r.norm), "successor_card": PREDECESSOR.get(r.norm),
                     "licence": LICENCES["rebench07" if src == "B" else "swebench-experiments"]})
    return rows


def task_rows(comp, link):
    fit = comp["fit"]
    tasks = pd.concat([split_tasks(sp) for sp in ("verified", "lite", "test", "multilingual")])
    srcs = tasks.groupby("instance_id").split.agg(lambda x: "+".join(sorted(set(x))))
    tasks = tasks.drop_duplicates("instance_id").set_index("instance_id")
    b_r = to_router(fit.b, link["alpha"], link["gamma"])
    rows = []
    for j, x in enumerate(comp["items"]):
        t = tasks.loc[x]
        rows.append({"id": f"swebench-{x}", "raw_id": x, "source": "swebench-" + srcs[x], "repo": t.repo,
                     "text": f"Repository: {t.repo}\n\n{t.problem_statement}",
                     "irt_b": round(float(fit.b[j]), 4), "irt_a": round(float(fit.a[j]), 4),
                     "se": round(float(fit.se_b[j]), 4), "irt_b_router": round(float(b_r[j]), 3),
                     "irt_b_router_scale": round(float(to_1_10(b_r[j])), 3),
                     "se_router": round(float(link["gamma"] * fit.se_b[j]), 3),
                     "n_systems": int(comp["n_sys_item"][j]),
                     "licence": LICENCES["swebench-tasks"] + "; outcomes: " + LICENCES["swebench-experiments"]})
    return rows


def gold_overlap(rows):
    gold = [json.loads(line) for line in (ROOT / "data" / "gold" / "gold.jsonl").open()]
    gtext = {norm_text(g["task"]["text"]): g["id"] for g in gold}
    graw = {(g.get("meta") or {}).get("raw_id"): g["id"] for g in gold}
    hits = []
    for r in rows:
        g = gtext.get(norm_text(r["text"])) or graw.get(r["raw_id"])
        if not g:  # near-duplicate: same problem statement body inside a gold text
            body = norm_text(r["text"].split("\n\n", 1)[-1])
            g = next((gid for gt, gid in gtext.items() if len(body) > 200 and body[:400] in gt), None)
        if g:
            hits.append({"task": r["id"], "gold": g})
    return hits


def profiler_eval(rows):
    from scipy.stats import spearmanr

    from panda_router.heuristic import HeuristicProfiler
    from panda_router.model.onnx_profiler import OnnxProfiler

    # issue text only: no patch-derived context (RESULTS.md limitation 4)
    tasks = [{"text": r["text"], "context": {"requires_tools": True, "has_images": False}} for r in rows]
    b = np.array([r["irt_b"] for r in rows])
    v1 = OnnxProfiler(ROOT / "artifacts" / "panda-router-v1")
    ev1 = np.concatenate([[p.expected_difficulty() for p in v1.profile_batch(tasks[j:j + 32])]
                          for j in range(0, len(tasks), 32)])
    heur = HeuristicProfiler()
    eh = np.array([heur.profile(t).expected_difficulty() for t in tasks])
    res = {}
    for name, e in (("v1", ev1), ("heuristic", eh)):
        rng = np.random.default_rng(0)
        boots = [spearmanr(e[ix], b[ix])[0] for ix in (rng.integers(0, len(b), len(b)) for _ in range(500))]
        res[name] = {"spearman": float(spearmanr(e, b)[0]), "ci95": [float(np.percentile(boots, 2.5)),
                                                                     float(np.percentile(boots, 97.5))],
                     "mean_expected_difficulty": float(e.mean())}
        for sp in ("verified", "lite", "multilingual"):
            m = np.array([sp in r["source"] for r in rows])
            res[name][f"spearman_{sp}"] = float(spearmanr(e[m], b[m])[0])
    return res, ev1, eh


def main():
    oa, sa = load_swebench()
    oa = oa[oa.source != "swebench-multimodal"]
    oa, sa, renamed = link_multilingual(oa, sa)
    sa = sa.assign(kind="scaffold_submission")
    ob, sb = load_rebench07()
    sb = sb.assign(norm=sb.base_model_raw.map(norm_model), agent=sb.scaffold, kind=sb.type)

    comps, links, sys_rows = {}, {}, []
    for name, out, sysdf in (("A", oa, sa), ("B", ob, sb)):
        comps[name] = fit_component(out, name)
        links[name] = link_component(comps[name], sysdf)
        print(name, {k: v for k, v in links[name].items() if k != "anchors"}, flush=True)
        sys_rows += systems_rows(comps[name], sysdf, links[name], name)

    rows = task_rows(comps["A"], links["A"])
    overlap = gold_overlap(rows)
    drop = {h["task"] for h in overlap}
    rows = [r for r in rows if r["id"] not in drop]
    with (OUT / "tasks.jsonl").open("w") as f:
        f.writelines(json.dumps(r) + "\n" for r in rows)
    with (OUT / "systems.jsonl").open("w") as f:
        f.writelines(json.dumps(r, default=str) + "\n" for r in sys_rows)

    summary = {
        "components": {k: {"n_systems": len(c["systems"]), "n_items": len(c["items"]), "n_cells": c["cells"],
                           "n_trials": c["trials"], "model": "2PL" if c["fit"].two_pl else "1PL",
                           "heldout": c["diag"], "median_a": float(np.median(c["fit"].a)),
                           "link": links[k]} for k, c in comps.items()},
        "multilingual_linked_systems": renamed,
        "gold_overlap": overlap, "n_tasks_written": len(rows),
        "multimodal_excluded": {"systems": int((sa.source == "swebench-multimodal").sum()),
                                "reason": "no shared system or task with the other splits (unlinked scale)"},
    }
    if "--no-eval" not in sys.argv:
        summary["profiler_eval"], ev1, eh = profiler_eval(rows)
        pd.DataFrame({"id": [r["id"] for r in rows], "irt_b": [r["irt_b"] for r in rows], "v1": ev1,
                      "heuristic": eh}).to_csv(OUT / "raw" / "profiler_eval.csv", index=False)
    (OUT / "fit.json").write_text(json.dumps(summary, indent=1, default=str))
    print(json.dumps({k: v for k, v in summary.items() if k != "components"}, default=str)[:2000])


if __name__ == "__main__":
    main()
