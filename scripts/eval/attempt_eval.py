"""Score a profiler on held-out gold attempt-and-grade outcomes.

Example:
  .venv/bin/python scripts/eval/attempt_eval.py --profiler onnx:artifacts/panda-router-v3 \
    --out eval_reports/v3/attempt_v3.json
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from panda_router.eval.attempts import evaluate_attempts, markdown  # noqa: E402
from panda_router.eval.baselines import load_profiler  # noqa: E402
from panda_router.eval.gold import read_jsonl  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profiler", required=True, help="onnx:<artifacts> | torch:<checkpoint>")
    ap.add_argument("--out", required=True)
    ap.add_argument("--gold", default="data/outcomes/gold_attempts.jsonl")
    ap.add_argument("--attempts", default="data/outcomes/attempts.jsonl")
    ap.add_argument("--gold-tasks", default="data/gold/gold.jsonl")
    ap.add_argument("--cards", default=None)
    args = ap.parse_args()

    task_by_id = {row["id"]: row["task"] for row in read_jsonl(args.gold_tasks)}
    report = {"profiler": args.profiler, **evaluate_attempts(load_profiler(args.profiler), read_jsonl(args.gold),
              read_jsonl(args.attempts), task_by_id, args.cards)}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    out.with_suffix(".md").write_text(markdown(report))
    print(markdown(report), end="")


if __name__ == "__main__":
    main()
