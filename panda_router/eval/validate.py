"""Validate labelled examples against schemas/CONTRACTS.md field rules."""

from __future__ import annotations

import json
from pathlib import Path

from ..taxonomy import CATEGORIES, CHECKLIST_IDS, FLAGS, N_DIFFICULTY, N_SKILL_LEVELS, SKILL_AXES

SOURCES = {"synthetic", "swe-rebench", "wildchat", "swe-smith", "minimal-pair"}
TOL = 1e-3


def _dist(x, n: int, name: str) -> list[str]:
    if not isinstance(x, list) or len(x) != n:
        return [f"{name}: expected list of {n}"]
    if any((not isinstance(v, (int, float))) or v < -TOL for v in x):
        return [f"{name}: negative or non-numeric entry"]
    return [] if abs(sum(x) - 1) <= TOL else [f"{name}: sums to {sum(x):.4f}"]


def validate_example(ex: dict) -> list[str]:
    errs = []
    for k in ("id", "source", "task", "labels"):
        if k not in ex:
            errs.append(f"missing {k}")
    if errs:
        return errs
    if ex["source"] not in SOURCES:
        errs.append(f"bad source {ex['source']}")
    if "pair_of" not in ex:
        errs.append("missing pair_of")
    t = ex["task"]
    if not isinstance(t.get("text"), str) or not t["text"].strip():
        errs.append("task.text empty")
    if not isinstance(t.get("context", {}), dict):
        errs.append("task.context not a dict")
    lab = ex["labels"]
    cat = lab.get("category") or {}
    if any(c not in CATEGORIES for c in cat):
        errs.append(f"unknown category in {list(cat)}")
    if any(v < -TOL or v > 1 + TOL for v in cat.values()) or abs(sum(cat.values()) - 1) > TOL:
        errs.append(f"category does not sum to 1 ({sum(cat.values()):.4f})")
    errs += _dist(lab.get("difficulty"), N_DIFFICULTY, "difficulty")
    sk = lab.get("skills") or {}
    if set(sk) != set(SKILL_AXES):
        errs.append(f"skills axes mismatch: {sorted(set(SKILL_AXES) ^ set(sk))}")
    for ax in SKILL_AXES:
        if ax in sk:
            errs += _dist(sk[ax], N_SKILL_LEVELS, f"skills.{ax}")
    for field, ids in (("flags", FLAGS), ("checklist", CHECKLIST_IDS)):
        d = lab.get(field) or {}
        if set(d) != set(ids):
            errs.append(f"{field} ids mismatch: {sorted(set(ids) ^ set(d))}")
        if any(not (0 - TOL <= float(v) <= 1 + TOL) for v in d.values()):
            errs.append(f"{field}: value outside [0,1]")
    o = lab.get("out_tokens_log10")
    if not isinstance(o, (int, float)) or not (0 <= o <= 6):
        errs.append(f"out_tokens_log10 invalid: {o}")
    return errs


def validate_file(path) -> list[str]:
    errs, ids = [], set()
    for i, line in enumerate(Path(path).read_text().splitlines()):
        if not line.strip():
            continue
        ex = json.loads(line)
        if ex.get("id") in ids:
            errs.append(f"line {i + 1}: duplicate id {ex.get('id')}")
        ids.add(ex.get("id"))
        errs += [f"line {i + 1} ({ex.get('id')}): {e}" for e in validate_example(ex)]
    return errs
