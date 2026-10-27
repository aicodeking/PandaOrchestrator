"""Build fair current-label test subsets from a historical training split."""

from __future__ import annotations


def fresh_rows(rows: list[dict], reference_train_ids: set[str]) -> list[dict]:
    """Keep current rows whose ids were not in the comparison model's train split."""
    return [row for row in rows if row.get("id") not in reference_train_ids]
