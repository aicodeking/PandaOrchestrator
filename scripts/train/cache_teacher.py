"""Cache teacher raw head outputs for the train split once.
.venv/bin/python scripts/train/cache_teacher.py --teacher checkpoints/t400m/best --data-dir data \
    --out checkpoints/cache/t400m_train.pt
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from panda_router.train.distill import cache_teacher  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--teacher", required=True)
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out", required=True)
    ap.add_argument("--split", default="train")
    ap.add_argument("--device", default=None)
    ap.add_argument("--extra", default=None, help="also cache these outcome-anchor rows (same file as --outcome-anchors)")
    a = ap.parse_args()
    print(cache_teacher(a.teacher, a.data_dir, a.out, a.split, a.device, extra=a.extra))


if __name__ == "__main__":
    main()
