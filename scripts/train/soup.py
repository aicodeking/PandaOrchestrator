"""Greedy soup over seed runs (same backbone), then fit per-head temperatures on val.
.venv/bin/python scripts/train/soup.py --runs checkpoints/s32m_seed{0,1,2} --data-dir data --out checkpoints/s32m_soup
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from panda_router.train.calibrate import calibrate_checkpoint  # noqa: E402
from panda_router.train.soup import greedy_soup  # noqa: E402
from panda_router.train.trainer import pick_device  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", nargs="+", required=True, help="run dirs (or their best/ dirs)")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default=None)
    ap.add_argument("--no-calibrate", action="store_true")
    a = ap.parse_args()
    report = greedy_soup(a.runs, a.data_dir, a.out, a.device)
    if not a.no_calibrate:
        report["calibration"] = calibrate_checkpoint(a.out, a.data_dir, device=pick_device(a.device))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
