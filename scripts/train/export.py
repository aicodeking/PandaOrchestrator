"""Export a calibrated checkpoint to artifacts/<name>/ (fp32 + int8 ONNX, tokenizer, heads.json, metrics.json).
.venv/bin/python scripts/train/export.py --ckpt checkpoints/s32m_soup --data-dir data --out artifacts/profiler-32m
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from panda_router.train.export import export_artifacts  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-drop", type=float, default=1.0, help="max per-head int8 drop in points (0..100 scale)")
    ap.add_argument("--opset", type=int, default=17)
    ap.add_argument("--per-channel", action="store_true", help="per-channel int8 weights (better for 150M)")
    a = ap.parse_args()
    m = export_artifacts(a.ckpt, a.out, a.data_dir, a.max_drop, a.opset, per_channel=a.per_channel)
    print(json.dumps({k: m[k] for k in ("int8_drops_points", "int8_within_tolerance", "torch_vs_onnx_max_abs",
                                        "size_mb")}, indent=2))


if __name__ == "__main__":
    main()
