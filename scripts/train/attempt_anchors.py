"""Build precision-weighted row-level anchors from attempt-and-grade IRT data.

Writes ``<out>/{train,val}.jsonl`` for use with ``train.py --anchors``.  The
gold attempt set is deliberately never read: it remains a held-out evaluator.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from panda_router.train.attempt_anchors import build_rows  # noqa: E402
from panda_router.train.data import load_jsonl  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tasks", default="data/outcomes/tasks_attempts.jsonl")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out", default="checkpoints/attempt_outcome")
    ap.add_argument("--min-models", type=int, default=4)
    args = ap.parse_args()

    tasks = load_jsonl(args.tasks)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    summary = {}
    task_ids = {r["task_id"] for r in tasks}
    summary["stale_or_unavailable_ids"] = len(task_ids - set().union(*(
        {r["id"] for r in load_jsonl(Path(args.data_dir) / f"{s}.jsonl")} for s in ("train", "val", "test")
    )))
    for split in ("train", "val"):
        ids = {r["id"] for r in load_jsonl(Path(args.data_dir) / f"{split}.jsonl")}
        available = task_ids & ids
        rows = build_rows(tasks, ids, args.min_models)
        (out / f"{split}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        summary[split] = {
            "available": len(available),
            "informative": len(rows),
            "mean_weight": round(sum(r["w"] for r in rows) / len(rows), 4) if rows else 0.0,
        }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
