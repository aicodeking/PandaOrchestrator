"""End-to-end evaluation of one profiler on a labelled split: profiler metrics, routing metrics
(oracle vs predicted through the real matcher, plus fixed-pick baselines), latency, anchors."""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from .baselines import label_profile, load_profiler
from .gold import read_jsonl
from .metrics import profiler_metrics

ROOT = Path(__file__).resolve().parent.parent.parent
SPLITS = {"gold": ROOT / "data" / "gold" / "gold.jsonl", "test": ROOT / "data" / "test.jsonl",
          "val": ROOT / "data" / "val.jsonl"}
ANCHORS = ROOT / "data" / "gold" / "anchors.jsonl"


def load_split(split: str, path: str | Path | None = None) -> list[dict]:
    p = Path(path) if path else SPLITS[split]
    rows = [r for r in read_jsonl(p) if "labels" in r]
    if not rows:
        raise FileNotFoundError(f"no labelled rows in {p}")
    return rows


def profile_all(profiler, tasks: list[dict]) -> tuple[list, dict]:
    preds, times = [], []
    for t in tasks:
        t0 = time.perf_counter()
        preds.append(profiler.profile(t))
        times.append((time.perf_counter() - t0) * 1000.0)
    a = np.asarray(times)
    return preds, {"n": len(a), "p50_ms": round(float(np.percentile(a, 50)), 3),
                   "p95_ms": round(float(np.percentile(a, 95)), 3), "mean_ms": round(float(a.mean()), 3)}


def _by_source(rows, preds) -> dict:
    out = {}
    for src in sorted({r["source"] for r in rows}):
        idx = [i for i, r in enumerate(rows) if r["source"] == src]
        if len(idx) >= 5:
            m = profiler_metrics([rows[i]["labels"] for i in idx], [preds[i] for i in idx])
            out[src] = {"n": len(idx), "category_acc": m["category"]["acc"], "difficulty_mae": m["difficulty"]["mae"],
                        "difficulty_spearman": m["difficulty"]["spearman"], "flags_f1": m["flags"]["f1_macro"],
                        "checklist_f1": m["checklist"]["f1_macro"]}
    return out


def run_eval(profiler_spec: str, split: str = "gold", data_path: str | None = None, n_pools: int = 500,
             pools_per_task: int | None = 50, cards_dir: str | None = None, seed: int = 0,
             train_path: str | None = None, profiler=None, skip_routing: bool = False) -> dict:
    rows = load_split(split, data_path)
    tasks = [r["task"] for r in rows]
    profiler = profiler or load_profiler(profiler_spec, train_path=train_path)
    preds, latency = profile_all(profiler, tasks)
    pred_dicts = [p.to_dict() for p in preds]
    anchors = {a["id"]: a for a in read_jsonl(ANCHORS)} if split == "gold" else {}
    anchor_vals = [anchors[r["id"]]["irt_b"] if r["id"] in anchors else None for r in rows] if anchors else None
    report = {
        "profiler": profiler_spec, "split": split, "data": str(data_path or SPLITS[split]), "n": len(rows),
        "sources": {s: sum(r["source"] == s for r in rows) for s in sorted({r["source"] for r in rows})},
        "latency": latency,
        "profiler_metrics": profiler_metrics([r["labels"] for r in rows], pred_dicts, anchor_vals),
        "by_source": _by_source(rows, pred_dicts),
    }
    if not skip_routing:
        from .routing import RoutingEvaluator

        ev = RoutingEvaluator(cards_dir=cards_dir, n_pools=n_pools, pools_per_task=pools_per_task, seed=seed)
        oracle = [label_profile(r["labels"]) for r in rows]
        t0 = time.perf_counter()
        report["routing"] = ev.evaluate(tasks, oracle, {"predicted": preds})
        report["routing"]["wall_s"] = round(time.perf_counter() - t0, 1)
    return report


def _f(x, nd=3):
    return "-" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def markdown_summary(rep: dict) -> str:
    m = rep["profiler_metrics"]
    lines = [f"# Eval: `{rep['profiler']}` on `{rep['split']}` (n={rep['n']})", "",
             f"Sources: {rep['sources']}  ", f"Latency (batch 1): p50 {rep['latency']['p50_ms']} ms, p95 {rep['latency']['p95_ms']} ms", "",
             "## Profiler", "", "| head | metric | value |", "|---|---|---|",
             f"| category | acc / top2 / ECE | {_f(m['category']['acc'])} / {_f(m['category']['top2'])} / {_f(m['category']['ece'])} |",
             f"| difficulty | MAE / Spearman / QWK / ECE | {_f(m['difficulty']['mae'])} / {_f(m['difficulty']['spearman'])} / "
             f"{_f(m['difficulty']['qwk'])} / {_f(m['difficulty']['ece'])} |",
             f"| skills | mean MAE / mean Spearman / mean ECE | {_f(m['skills']['mae_mean'])} / {_f(m['skills']['spearman_mean'])} / {_f(m['skills']['ece_mean'])} |",
             f"| flags | F1 macro / AUROC macro / ECE | {_f(m['flags']['f1_macro'])} / {_f(m['flags']['auroc_macro'])} / {_f(m['flags']['ece_macro'])} |",
             f"| checklist | F1 macro / micro / AUROC | {_f(m['checklist']['f1_macro'])} / {_f(m['checklist']['f1_micro'])} / {_f(m['checklist']['auroc_macro'])} |",
             f"| out_tokens | MAE log10 / p10-p90 coverage | {_f(m['out_tokens']['mae_log10'])} / {_f(m['out_tokens']['coverage_p10_p90'])} |"]
    d = m["difficulty"]
    if "anchor_n" in d:
        lines += [f"| difficulty vs IRT anchors | Spearman pred / label (n={d['anchor_n']}) | "
                  f"{_f(d['spearman_pred_vs_anchor'])} / {_f(d['spearman_label_vs_anchor'])} |"]
    if rep.get("by_source"):
        lines += ["", "### By source", "", "| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |", "|---|---|---|---|---|---|---|"]
        lines += [f"| {s} | {v['n']} | {_f(v['category_acc'])} | {_f(v['difficulty_mae'])} | {_f(v['difficulty_spearman'])} | "
                  f"{_f(v['flags_f1'])} | {_f(v['checklist_f1'])} |" for s, v in rep["by_source"].items()]
    if r := rep.get("routing"):
        lines += ["", f"## Routing (cards: {r['card_source']}, {r['n_pools']} pools, {r['pools_per_task']} pools/task)", "",
                  "| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |",
                  "|---|---|---|---|---|---|---|---|---|---|---|"]
        for name, modes in r["metrics"].items():
            for mode, v in modes.items():
                if v.get("n"):
                    lines.append(f"| {name} | {mode} | {v['n']} | {_f(v['pick_agreement'])} | {_f(v['utility_regret'], 4)} | "
                                 f"{_f(v['cost_ratio'])} | {_f(v['p_success'])} | {_f(v.get('below_min_p_rate'))} | {_f(v['pq_quality'])} | {_f(v['pq_quality_oracle'])} | "
                                 f"{_f(v['infeasible_rate'])} |")
    return "\n".join(lines) + "\n"


def save_report(rep: dict, out: str | Path) -> tuple[Path, Path]:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=2))
    md = out.with_suffix(".md")
    md.write_text(markdown_summary(rep))
    return out, md
