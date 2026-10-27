"""Evaluation against the held-out, graded gold-attempt outcome set."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

from .routing import card_price, card_strength

ATTEMPTERS = (
    "openrouter-deepseek-v4.1-flash",
    "openrouter-qwen3.8-flash",
    "openrouter-minimax-m3.1-flash",
    "openrouter-gemini-3.8-flash",
    "openrouter-gpt-6.1-sol",
)


def observed_cells(rows: list[dict], pool: tuple[str, ...] = ATTEMPTERS) -> dict[tuple[str, str], dict]:
    """Index real graded gold outcomes, retaining the actual attempt cost."""
    return {
        (row["task_id"], row["model"]): row
        for row in rows
        if row.get("split") == "gold" and row.get("model") in pool and row.get("pass") is not None
        and row.get("cost_attempt") is not None
    }


def score_picks(picks: dict[str, str], cells: dict[tuple[str, str], dict]) -> dict:
    """Score one pick per task only from observed pass/fail and logged attempt cost."""
    selected = [cells[(task_id, model)] for task_id, model in picks.items()]
    costs = [float(row["cost_attempt"]) for row in selected]
    return {
        "n": len(selected),
        "success_per_100": round(100 * float(np.mean([bool(row["pass"]) for row in selected])), 1) if selected else None,
        "cost_per_100_usd": round(100 * float(np.mean(costs)), 3) if costs else None,
        "picks": dict(sorted(Counter(picks.values()).items())),
    }


def _task(row: dict, task_by_id: dict[str, dict]) -> dict:
    return task_by_id.get(row["task_id"], {"text": row["text"], "context": {}})


def evaluate_attempts(profiler, gold_rows: list[dict], attempt_rows: list[dict], task_by_id: dict[str, dict],
                      cards_dir: str | Path | None = None, pool: tuple[str, ...] = ATTEMPTERS) -> dict:
    """Evaluate difficulty ranking and actual routing success on gold attempt outcomes.

    Difficulty Spearman uses every gold item with a fitted IRT difficulty.  The
    routing table is intentionally stricter: it uses only tasks whose every
    candidate model has a real grade and logged attempt cost.
    """
    from ..matcher import Matcher, load_cards

    cells = observed_cells(attempt_rows, pool)
    full = [row for row in gold_rows if all((row["task_id"], model) in cells for model in pool)]
    if not full:
        raise ValueError("no gold tasks have complete observed outcomes for the attempter pool")

    ranking_rows = [row for row in gold_rows if row.get("irt_b") is not None]
    pred = np.asarray([profiler.profile(_task(row, task_by_id)).expected_difficulty() for row in ranking_rows])
    irt_b = np.asarray([float(row["irt_b"]) for row in ranking_rows])
    rho = spearmanr(pred, irt_b).statistic

    cards = load_cards(cards_dir)
    missing = [model for model in pool if model not in cards]
    if missing:
        raise ValueError(f"attempter cards missing: {missing}")
    matcher = Matcher(cards_dir=cards_dir)
    strongest = max(pool, key=lambda model: (card_strength(cards[model]), model))
    cheapest = min(pool, key=lambda model: (card_price(cards[model]), model))
    tasks = {row["task_id"]: _task(row, task_by_id) for row in full}

    policies = {
        "always_cheapest": {task_id: cheapest for task_id in tasks},
        "always_strongest": {task_id: strongest for task_id in tasks},
    }
    for mode in ("cheapest_above_threshold", "max_utility", "max_quality"):
        policies[mode] = {
            task_id: matcher.route({"task": task, "pool": list(pool), "preferences": {"mode": mode},
                                    "return_top_k": len(pool)}, profiler.profile(task), trace_id="attempt-eval")["choice"]["model_id"]
            for task_id, task in tasks.items()
        }
    return {
        "attempt_irt": {
            "n": len(ranking_rows),
            "spearman": round(float(rho), 4) if np.isfinite(rho) else None,
            "mean_pred": round(float(pred.mean()), 3),
            "sd_pred": round(float(pred.std()), 3),
        },
        "routing": {
            "n": len(full),
            "pool": list(pool),
            "cost": "logged attempt cost only",
            "policies": {name: score_picks(picks, cells) for name, picks in policies.items()},
        },
    }


def markdown(report: dict) -> str:
    irt, routing = report["attempt_irt"], report["routing"]
    rows = ["# Gold attempt-and-grade outcome evaluation", "",
            f"IRT difficulty Spearman on held-out gold attempts (n={irt['n']}): **{irt['spearman']:.4f}** "
            f"(predicted mean/sd {irt['mean_pred']:.3f}/{irt['sd_pred']:.3f}).", "",
            f"True routed outcomes use the {routing['n']} gold tasks graded for every attempter; cost is {routing['cost']}.", "",
            "| policy | success / 100 | $ / 100 tasks | picks |", "|---|---:|---:|---|"]
    for name, value in routing["policies"].items():
        rows.append(f"| {name} | {value['success_per_100']:.1f} | {value['cost_per_100_usd']:.3f} | "
                    f"{', '.join(f'{m}: {n}' for m, n in value['picks'].items())} |")
    return "\n".join(rows) + "\n"
