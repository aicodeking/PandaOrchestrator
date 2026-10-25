"""Tabulate several eval reports side by side.

  .venv/bin/python scripts/eval/compare.py eval_reports/heuristic_gold.json eval_reports/knn_gold.json [--mode max_utility] [--out eval_reports/compare.md]
"""

import argparse
import json
import sys
from pathlib import Path

ROWS = [
    ("category acc", ("profiler_metrics", "category", "acc")),
    ("category top2", ("profiler_metrics", "category", "top2")),
    ("difficulty MAE", ("profiler_metrics", "difficulty", "mae")),
    ("difficulty Spearman", ("profiler_metrics", "difficulty", "spearman")),
    ("difficulty QWK", ("profiler_metrics", "difficulty", "qwk")),
    ("difficulty vs IRT (Spearman)", ("profiler_metrics", "difficulty", "spearman_pred_vs_anchor")),
    ("skills MAE (mean)", ("profiler_metrics", "skills", "mae_mean")),
    ("flags F1 macro", ("profiler_metrics", "flags", "f1_macro")),
    ("flags AUROC macro", ("profiler_metrics", "flags", "auroc_macro")),
    ("checklist F1 macro", ("profiler_metrics", "checklist", "f1_macro")),
    ("out_tokens MAE log10", ("profiler_metrics", "out_tokens", "mae_log10")),
    ("ECE category", ("profiler_metrics", "ece", "category")),
    ("ECE difficulty", ("profiler_metrics", "ece", "difficulty")),
    ("ECE flags", ("profiler_metrics", "ece", "flags_macro")),
    ("ECE checklist", ("profiler_metrics", "ece", "checklist_macro")),
    ("latency p50 ms", ("latency", "p50_ms")),
    ("latency p95 ms", ("latency", "p95_ms")),
]
ROUTE_KEYS = ["pick_agreement", "utility_regret", "cost_ratio", "p_success", "below_min_p_rate", "pq_quality", "infeasible_rate"]


def get(d, path):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def fmt(x):
    return "-" if x is None else (f"{x:.3f}" if isinstance(x, float) else str(x))


def table(reports: list[dict], names: list[str], mode: str) -> str:
    out = ["| metric | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    out += [f"| {label} | " + " | ".join(fmt(get(r, path)) for r in reports) + " |" for label, path in ROWS]
    for k in ROUTE_KEYS:
        out.append(f"| routing[{mode}] {k} | " + " | ".join(fmt(get(r, ("routing", "metrics", "predicted", mode, k))) for r in reports) + " |")
    base = next((r for r in reports if get(r, ("routing", "metrics"))), None)
    if base:
        out += ["", f"Fixed-pick baselines ({mode}, from {base['profiler']} run):", "", "| policy | " + " | ".join(ROUTE_KEYS) + " |",
                "|---|" + "---|" * len(ROUTE_KEYS)]
        for pol in ("always_strongest", "always_cheapest"):
            v = get(base, ("routing", "metrics", pol, mode)) or {}
            out.append(f"| {pol} | " + " | ".join(fmt(v.get(k)) for k in ROUTE_KEYS) + " |")
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("reports", nargs="+")
    ap.add_argument("--mode", default="all", help="routing mode column (all | cheapest_above_threshold | max_utility | max_quality)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    reps = [json.loads(Path(p).read_text()) for p in a.reports]
    names = [f"{r['profiler']}@{r['split']}" for r in reps]
    md = table(reps, names, a.mode)
    print(md)
    if a.out:
        Path(a.out).write_text(md)


if __name__ == "__main__":
    sys.exit(main())
