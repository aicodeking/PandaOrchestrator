"""Build the held-out GOLD set.

  .venv/bin/python scripts/eval/build_gold.py select            # data/gold/candidates.jsonl
  .venv/bin/python scripts/eval/build_gold.py label --teachers codex kimi ollama
  .venv/bin/python scripts/eval/build_gold.py merge             # data/gold/gold.jsonl + agreement.json
  .venv/bin/python scripts/eval/build_gold.py validate
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from panda_router.eval import gold  # noqa: E402
from panda_router.eval.validate import validate_file  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("select")
    s.add_argument("--n-rebench", type=int, default=120)
    s.add_argument("--n-smith", type=int, default=25)
    s.add_argument("--wild-per-cat", type=int, default=20)
    s.add_argument("--seed", type=int, default=0)
    l = sub.add_parser("label")
    l.add_argument("--teachers", nargs="+", default=list(gold.TEACHERS), choices=gold.TEACHERS)
    l.add_argument("--passes", type=int, default=2)
    l.add_argument("--limit", type=int, default=None)
    m = sub.add_parser("merge")
    m.add_argument("--min-teachers", type=int, default=2)
    sub.add_parser("fix-context")
    sub.add_parser("validate")
    a = ap.parse_args()

    if a.cmd == "select":
        print(json.dumps(gold.build_candidates(a.n_rebench, a.n_smith, a.wild_per_cat, a.seed), indent=2))
    elif a.cmd == "label":
        asyncio.run(gold.label(a.teachers, a.passes, a.limit))
    elif a.cmd == "merge":
        stats = gold.merge_gold(a.min_teachers)
        (gold.GOLD / "agreement.json").write_text(json.dumps(stats, indent=2))
        print(json.dumps(stats, indent=2))
    elif a.cmd == "fix-context":
        print(gold.refresh_contexts(), "SWE candidates refreshed")
    else:
        errs = validate_file(gold.GOLD_PATH)
        print(f"{len(errs)} errors")
        for e in errs[:20]:
            print(" ", e)
        sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
