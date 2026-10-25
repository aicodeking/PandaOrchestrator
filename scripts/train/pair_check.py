"""Minimal-pair sign check: % of (pair, expected_delta key) where the predicted change edited - original
has the expected sign.

  .venv/bin/python scripts/train/pair_check.py --profiler onnx:artifacts/panda-router-v1 --split test \
      --out eval_reports/pairs_v1_test.json

Quantities: difficulty / skills.<axis> -> expected level; flags.<id> / checklist.<id> -> probability.
Expected sign comes from meta.expected_delta (panda_router.model.losses.parse_delta). Keys with an
expected sign of 0 are skipped.
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402

from panda_router.eval.baselines import load_profiler  # noqa: E402
from panda_router.model.losses import parse_delta  # noqa: E402
from panda_router.train.data import load_jsonl  # noqa: E402


def quantity(profile, key: str):
    head, _, name = key.partition(".")
    if head == "difficulty":
        return float(np.dot(profile.difficulty, np.arange(1, 11)))
    if head == "skills" and name in profile.skills:
        return float(np.dot(profile.skills[name], np.arange(11)))
    if head in ("flags", "checklist"):
        return getattr(profile, head).get(name)
    return None


def pair_check(profiler, rows: list[dict]) -> dict:
    by_id = {r["id"]: r for r in rows}
    pairs = [r for r in rows if r.get("source") == "minimal-pair" and r.get("pair_of") in by_id]
    cache = {}

    def prof(r):
        if r["id"] not in cache:
            cache[r["id"]] = profiler.profile(r["task"])
        return cache[r["id"]]

    hits, per_key = [], defaultdict(list)
    for r in pairs:
        edit = (r.get("meta") or {}).get("edit", "?")
        for key, val in ((r.get("meta") or {}).get("expected_delta") or {}).items():
            sign = parse_delta(key, val)
            a, b = quantity(prof(r), key), quantity(prof(by_id[r["pair_of"]]), key)
            if not sign or a is None or b is None:
                continue
            ok = float(np.sign(a - b) == sign)
            hits.append(ok)
            per_key[f"{edit}: {key}"].append(ok)
    return {"n_pairs": len(pairs), "n_checks": len(hits), "sign_ok": float(np.mean(hits)) if hits else None,
            "per_key": {k: {"n": len(v), "sign_ok": float(np.mean(v))} for k, v in sorted(per_key.items())}}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profiler", required=True)
    ap.add_argument("--split", default="test")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    rep = {"profiler": a.profiler, "split": a.split,
           **pair_check(load_profiler(a.profiler), load_jsonl(Path(a.data_dir) / f"{a.split}.jsonl"))}
    print(json.dumps(rep, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()
