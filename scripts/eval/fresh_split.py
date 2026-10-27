"""Materialise a current-label fresh test split against a historical git training set.

The v3 data rebuild changed split membership and labels.  Filtering the current
test rows by ids from the v2 release commit keeps DeepSeek-updated labels while
removing tasks the v2 profiler could have trained on.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from panda_router.eval.fresh import fresh_rows  # noqa: E402
from panda_router.eval.gold import read_jsonl  # noqa: E402


def reference_ids(ref: str, path: str) -> set[str]:
    text = subprocess.check_output(["git", "show", f"{ref}:{path}"], text=True)
    return {json.loads(line)["id"] for line in text.splitlines() if line.strip()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference", default="f53f30e", help="v2 release commit/ref")
    ap.add_argument("--reference-path", default="data/train.jsonl")
    ap.add_argument("--data", default="data/test.jsonl")
    ap.add_argument("--out", default="checkpoints/test_fresh_v2.jsonl")
    args = ap.parse_args()

    seen = reference_ids(args.reference, args.reference_path)
    current = read_jsonl(args.data)
    fresh = fresh_rows(current, seen)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in fresh))
    print(json.dumps({"reference": args.reference, "reference_train_n": len(seen), "current_n": len(current),
                      "fresh_n": len(fresh), "out": str(out)}))


if __name__ == "__main__":
    main()
