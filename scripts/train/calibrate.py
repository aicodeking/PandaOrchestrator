"""(Re)fit per-head temperatures on val for a checkpoint; writes <ckpt>/heads.json.
.venv/bin/python scripts/train/calibrate.py --ckpt checkpoints/s32m_soup --data-dir data
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from panda_router.train.calibrate import calibrate_checkpoint  # noqa: E402
from panda_router.train.trainer import pick_device  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--device", default=None)
    a = ap.parse_args()
    print(json.dumps(calibrate_checkpoint(a.ckpt, a.data_dir, device=pick_device(a.device)), indent=2))


if __name__ == "__main__":
    main()
