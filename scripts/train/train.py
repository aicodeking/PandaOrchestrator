"""Train one profiler run (teacher or student). Example:
.venv/bin/python scripts/train/train.py --backbone jhu-clsp/ettin-encoder-32m --data-dir data \
    --out checkpoints/s32m_seed0 --epochs 6 --seed 0 --distill-from checkpoints/cache/t400m_train.pt
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from panda_router.train.trainer import TrainConfig, train  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backbone", default="jhu-clsp/ettin-encoder-32m")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--lr", type=float, default=None, help="default: 1e-4 (<=32m), 5e-5 (68m-150m), 3e-5 (400m)")
    ap.add_argument("--regret-weight", type=float, default=0.05, help="0 disables the regret loss (ablation)")
    ap.add_argument("--pair-weight", type=float, default=0.5, help="0 disables the minimal-pair loss (ablation)")
    ap.add_argument("--single-teacher-weight", type=float, default=0.5,
                    help="weight of the per-head label losses for meta.single_teacher records (pair loss unaffected)")
    ap.add_argument("--anchors", default=None, help="checkpoints/anchors_train.jsonl (outcome-anchor aux loss)")
    ap.add_argument("--anchor-weight", type=float, default=0.0)
    ap.add_argument("--distill-from", default=None, help="teacher cache .pt from scripts/train/cache_teacher.py")
    ap.add_argument("--distill-T", type=float, default=3.0)
    ap.add_argument("--distill-alpha", type=float, default=0.5)
    ap.add_argument("--patience", type=int, default=2)
    ap.add_argument("--max-len", type=int, default=512)
    ap.add_argument("--max-steps", type=int, default=None)
    ap.add_argument("--limit-train", type=int, default=None)
    ap.add_argument("--device", default=None)
    ap.add_argument("--no-bf16", action="store_true")
    ap.add_argument("--no-calibrate", action="store_true")
    a = ap.parse_args()
    cfg = TrainConfig(backbone=a.backbone, data_dir=a.data_dir, out=a.out, epochs=a.epochs, seed=a.seed,
                      batch_size=a.batch_size, lr=a.lr, regret_weight=a.regret_weight, pair_weight=a.pair_weight,
                      distill_from=a.distill_from, distill_T=a.distill_T, distill_alpha=a.distill_alpha,
                      patience=a.patience, max_len=a.max_len, max_steps=a.max_steps, limit_train=a.limit_train,
                      device=a.device, bf16=not a.no_bf16, calibrate=not a.no_calibrate,
                      single_teacher_weight=a.single_teacher_weight, anchors=a.anchors, anchor_weight=a.anchor_weight)
    s = train(cfg)
    print(json.dumps({k: s[k] for k in ("best_val_score", "epochs_run", "steps", "train_examples_per_s", "best_dir")}))


if __name__ == "__main__":
    main()
