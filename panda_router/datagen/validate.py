"""Validator for data/<split>.jsonl records against schemas/CONTRACTS.md."""

import json
import math
import sys
from pathlib import Path

from ..taxonomy import CATEGORIES, CHECKLIST_IDS, FLAGS, N_DIFFICULTY, N_SKILL_LEVELS, SKILL_AXES

SOURCES = {"synthetic", "swe-rebench", "wildchat", "swe-smith", "minimal-pair"}
CTX_TYPES = {"repo_languages": list, "files_in_scope": int, "estimated_input_tokens": int, "has_images": bool, "requires_tools": bool}
TOL = 1e-3


def _dist(name: str, v, n: int) -> list[str]:
    if not isinstance(v, list) or len(v) != n:
        return [f"{name}: expected list of length {n}"]
    if any(not isinstance(x, (int, float)) or isinstance(x, bool) or x < -TOL or math.isnan(x) for x in v):
        return [f"{name}: values must be non-negative numbers"]
    if abs(sum(v) - 1) > TOL:
        return [f"{name}: sums to {sum(v):.4f}, not 1"]
    return []


def _probs(name: str, v, ids: list[str]) -> list[str]:
    if not isinstance(v, dict) or set(v) != set(ids):
        missing, extra = set(ids) - set(v or {}), set(v or {}) - set(ids)
        return [f"{name}: missing={sorted(missing)} extra={sorted(extra)}"]
    return [f"{name}.{k}: {x} not in [0,1]" for k, x in v.items()
            if not isinstance(x, (int, float)) or isinstance(x, bool) or not -TOL <= x <= 1 + TOL]


def validate_record(r: dict) -> list[str]:
    errs = []
    for k in ("id", "source", "pair_of", "task", "labels", "meta"):
        if k not in r:
            errs.append(f"missing {k}")
    if errs:
        return errs
    if not isinstance(r["id"], str) or not r["id"]:
        errs.append("id must be a non-empty string")
    if r["source"] not in SOURCES:
        errs.append(f"bad source {r['source']}")
    if r["source"] == "minimal-pair":
        if not isinstance(r["pair_of"], str):
            errs.append("minimal-pair needs pair_of")
        if "edit" not in r["meta"] or not isinstance(r["meta"].get("expected_delta"), dict):
            errs.append("minimal-pair needs meta.edit and meta.expected_delta")
    elif r["pair_of"] is not None:
        errs.append("pair_of must be null for non minimal-pair")
    t = r["task"]
    if not isinstance(t, dict) or not isinstance(t.get("text"), str) or not t["text"].strip():
        errs.append("task.text must be a non-empty string")
    ctx = t.get("context", {}) if isinstance(t, dict) else None
    if not isinstance(ctx, dict):
        errs.append("task.context must be an object")
    else:
        for k, v in ctx.items():
            typ = CTX_TYPES.get(k)
            if typ and (not isinstance(v, typ) or (typ is int and isinstance(v, bool))):
                errs.append(f"context.{k} must be {typ.__name__}")
    L = r["labels"]
    if not isinstance(L, dict):
        return errs + ["labels must be an object"]
    cat = L.get("category")
    if not isinstance(cat, dict) or not cat or set(cat) - set(CATEGORIES):
        errs.append("category must be a non-empty dict over taxonomy categories")
    elif abs(sum(cat.values()) - 1) > TOL or any(v < -TOL for v in cat.values()):
        errs.append(f"category sums to {sum(cat.values()):.4f}")
    errs += _dist("difficulty", L.get("difficulty"), N_DIFFICULTY)
    sk = L.get("skills")
    if not isinstance(sk, dict) or set(sk) != set(SKILL_AXES):
        errs.append("skills must have every axis")
    else:
        for ax in SKILL_AXES:
            errs += _dist(f"skills.{ax}", sk[ax], N_SKILL_LEVELS)
    errs += _probs("flags", L.get("flags"), FLAGS)
    errs += _probs("checklist", L.get("checklist"), CHECKLIST_IDS)
    o = L.get("out_tokens_log10")
    if not isinstance(o, (int, float)) or isinstance(o, bool) or not 0 <= o <= 6:
        errs.append("out_tokens_log10 must be a number in [0, 6]")
    if not isinstance(r["meta"], dict):
        errs.append("meta must be an object")
    return errs


def validate_file(path, check_pairs_in: set[str] | None = None) -> tuple[int, list[str]]:
    """Return (n_records, errors). Also checks duplicate ids."""
    errors, ids, n = [], set(), 0
    for lineno, line in enumerate(Path(path).read_text().splitlines(), 1):
        if not line.strip():
            continue
        n += 1
        try:
            r = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"{path}:{lineno}: invalid JSON ({e})")
            continue
        for e in validate_record(r):
            errors.append(f"{path}:{lineno} {r.get('id')}: {e}")
        if r.get("id") in ids:
            errors.append(f"{path}:{lineno}: duplicate id {r.get('id')}")
        ids.add(r.get("id"))
    return n, errors


def validate_splits(data_dir) -> dict:
    """Validate train/val/test, ids unique across splits, minimal pairs in their original's split."""
    data_dir = Path(data_dir)
    report, all_ids, split_of = {}, {}, {}
    pairs = []
    for s in ("train", "val", "test"):
        p = data_dir / f"{s}.jsonl"
        n, errs = validate_file(p)
        for line in p.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("id") in all_ids:
                    errs.append(f"id {r['id']} in both {all_ids[r['id']]} and {s}")
                all_ids[r.get("id")] = s
                split_of[r.get("id")] = s
                if r.get("source") == "minimal-pair":
                    pairs.append((r["id"], r["pair_of"], s))
        report[s] = {"n": n, "errors": errs}
    for pid, orig, s in pairs:
        if split_of.get(orig) != s:
            report[s]["errors"].append(f"minimal pair {pid} in {s} but original {orig} in {split_of.get(orig)}")
    return report


def main(argv=None) -> int:
    d = (argv or sys.argv[1:] or ["data"])[0]
    rep = validate_splits(d)
    bad = 0
    for s, v in rep.items():
        print(f"{s}: {v['n']} records, {len(v['errors'])} errors")
        for e in v["errors"][:20]:
            print("  ", e)
        bad += len(v["errors"])
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
