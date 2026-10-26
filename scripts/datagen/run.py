#!/usr/bin/env python
"""Panda Router dataset pipeline CLI. Every stage is resumable: re-running skips finished work
(teacher responses are cached in data/cache/calls, outputs appended to data/cache/{pool,labels,pairwise}).

  .venv/bin/python scripts/datagen/run.py real --rebench 1400 --smith 900 --wild 1700
  .venv/bin/python scripts/datagen/run.py generate --batches 280
  .venv/bin/python scripts/datagen/run.py label --what originals [--real-limit 60]
  .venv/bin/python scripts/datagen/run.py pairs --n 1100        # minimal-pair edits
  .venv/bin/python scripts/datagen/run.py label --what pairs
  .venv/bin/python scripts/datagen/run.py tiebreak
  .venv/bin/python scripts/datagen/run.py pairwise --pairs 3000
  .venv/bin/python scripts/datagen/run.py build                 # merge, BT, dedup, split, validate, STATS.md
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from panda_router.datagen import generate, hard, minimal_pairs, pipeline, real  # noqa: E402
from panda_router.datagen.common import sha_int  # noqa: E402


def _select(originals, real_limit):
    if real_limit is None:
        return originals
    reals = sorted((r for r in originals if r["source"] != "synthetic"), key=lambda r: sha_int(r["id"]))[:real_limit]
    return [r for r in originals if r["source"] == "synthetic"] + reals


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("real")
    p.add_argument("--rebench", type=int, default=1400)
    p.add_argument("--smith", type=int, default=900)
    p.add_argument("--wild", type=int, default=1700)
    p.add_argument("--download", action="store_true")
    sub.add_parser("fix-context", help="rewrite SWE contexts from issue text only (leak fix)")
    p = sub.add_parser("generate")
    p.add_argument("--batches", type=int, required=True)
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--teachers", default="codex,kimi")
    sub.add_parser("hard", help="generate hard / deceptive / scary-easy synthetic tasks")
    p = sub.add_parser("label")
    p.add_argument("--what", choices=["originals", "pairs", "all"], default="all")
    p.add_argument("--teachers", default="codex,grok")
    p.add_argument("--real-limit", type=int, default=None)
    p.add_argument("--need-second", action="store_true", help="only tasks with < 2 full-label teacher answers so far")
    p.add_argument("--synthetic-batches", type=int, default=None, help="only label synthetic tasks from batches < N")
    p = sub.add_parser("pairs")
    p.add_argument("--n", type=int, required=True)
    p.add_argument("--real-limit", type=int, default=None)
    p = sub.add_parser("tiebreak")
    p.add_argument("--limit", type=int, default=None)
    p = sub.add_parser("pairwise")
    p.add_argument("--pairs", type=int, default=3000)
    p = sub.add_parser("build")
    p.add_argument("--single-teacher-pairs", action="store_true", help="keep minimal pairs labelled by only one teacher")
    a = ap.parse_args()

    if a.cmd == "real":
        if a.download:
            real.download()
        print(real.build(a.rebench, a.smith, a.wild))
    elif a.cmd == "fix-context":
        print(real.refresh_contexts())
    elif a.cmd == "generate":
        asyncio.run(generate.generate(a.batches, a.start, teachers_=tuple(a.teachers.split(","))))
    elif a.cmd == "hard":
        asyncio.run(hard.generate())
    elif a.cmd == "label":
        originals, pairs = pipeline.load_pool()
        originals = _select(originals, a.real_limit)
        if a.synthetic_batches is not None:
            originals = [r for r in originals if r["source"] != "synthetic" or r["meta"]["gen_batch"] < a.synthetic_batches]
        if a.need_second:
            ans = pipeline.load_all_answers()
            originals = [r for r in originals if len(pipeline.answers_for(r["id"], ans)[1]) < 2]
        ids = {r["id"] for r in originals}
        tasks = {"originals": originals, "pairs": [p for p in pairs if p["pair_of"] in ids],
                 "all": originals + [p for p in pairs if p["pair_of"] in ids]}[a.what]
        print(f"labelling {len(tasks)} tasks with {a.teachers}", flush=True)
        asyncio.run(pipeline.label_all(tasks, teachers_=tuple(a.teachers.split(","))))
    elif a.cmd == "pairs":
        originals, _ = pipeline.load_pool(include_pairs=False)
        ans = pipeline.load_all_answers()
        labelled = [r for r in _select(originals, a.real_limit) if len(pipeline.answers_for(r["id"], ans)[1]) >= 2]
        print(f"{len(labelled)} labelled originals available for minimal pairs", flush=True)
        asyncio.run(minimal_pairs.make_pairs(labelled, a.n))
    elif a.cmd == "tiebreak":
        originals, pairs = pipeline.load_pool()
        print("tie-broken:", asyncio.run(pipeline.tiebreak(originals + pairs, a.limit)))
    elif a.cmd == "pairwise":
        originals, _ = pipeline.load_pool(include_pairs=False)
        asyncio.run(pipeline.run_pairwise(originals, a.pairs))
    elif a.cmd == "build":
        rep = pipeline.finalize(single_teacher_pairs=a.single_teacher_pairs)
        print(rep["validation"], rep["dedup"]["near_dup_dropped"], rep.get("bt"))


if __name__ == "__main__":
    main()
