"""Evaluate a profiler on a labelled split.

  .venv/bin/python scripts/eval/run_eval.py --profiler heuristic --split gold --out eval_reports/heuristic_gold.json
  .venv/bin/python scripts/eval/run_eval.py --profiler knn --split gold --out eval_reports/knn_gold.json
  .venv/bin/python scripts/eval/run_eval.py --profiler onnx:artifacts/<dir> --split gold --out eval_reports/onnx_gold.json
  .venv/bin/python scripts/eval/run_eval.py --profiler torch:checkpoints/<ckpt> --split test --out eval_reports/torch_test.json

Writes the JSON report and a markdown summary next to it (<out>.md).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from panda_router.eval.runner import markdown_summary, run_eval, save_report  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiler", required=True, help="heuristic | knn | onnx:<artifacts_dir> | torch:<checkpoint_dir>")
    ap.add_argument("--split", default="gold", choices=["gold", "test", "val"])
    ap.add_argument("--data", default=None, help="override the split's jsonl path")
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-pools", type=int, default=500)
    ap.add_argument("--pools-per-task", type=int, default=50, help="random pools per task (0 = all pools)")
    ap.add_argument("--cards", default=None, help="cards dir (default cards/, synthetic if missing)")
    ap.add_argument("--train", default=None, help="kNN training data (default data/train.jsonl)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--skip-routing", action="store_true")
    a = ap.parse_args()
    rep = run_eval(a.profiler, a.split, a.data, a.n_pools, a.pools_per_task or None, a.cards, a.seed, a.train,
                   skip_routing=a.skip_routing)
    js, md = save_report(rep, a.out)
    print(markdown_summary(rep))
    print(f"wrote {js} and {md}")


if __name__ == "__main__":
    main()
