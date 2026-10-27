"""Prepare trustworthy row-level anchors from the non-SWE attempt-and-grade IRT fit."""

from __future__ import annotations

import math

SE_REF = 0.5
MIN_WEIGHT = 0.05


def trust_weight(se: float, se_ref: float = SE_REF, minimum: float = MIN_WEIGHT) -> float:
    """Bound inverse-variance trust so uncertain IRT fits cannot dominate labels."""
    if not math.isfinite(se) or se <= 0:
        return minimum
    return max(minimum, min(1.0, (se_ref / se) ** 2))


def build_rows(tasks: list[dict], known_ids: set[str], min_models: int = 4) -> list[dict]:
    """Return informative anchors keyed to their current labelled records.

    All-pass/all-fail items are mostly prior-driven in this five-model IRT fit,
    and rows with fewer than ``min_models`` attempts are especially uncertain.
    Excluding them follows the outcome report's recommended censoring guard.
    The caller supplies ids from the current data split: the historical split in
    ``tasks_attempts.jsonl`` predates the v3 data rebuild and is not reliable.
    """
    rows = []
    for task in tasks:
        if task.get("task_id") not in known_ids:
            continue
        n_models, n_pass = int(task["n_models"]), int(task["n_pass"])
        if n_models < min_models or not 0 < n_pass < n_models:
            continue
        se = float(task["se"])
        rows.append({
            "id": task["task_id"],
            "source": "attempt-irt-anchor",
            "difficulty_1_10": float(task["irt_b_router_scale"]),
            "w": round(trust_weight(se), 6),
            "irt_b": float(task["irt_b"]),
            "se": se,
            "n_models": n_models,
            "n_pass": n_pass,
        })
    return rows
