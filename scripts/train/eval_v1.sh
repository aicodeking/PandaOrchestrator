#!/bin/sh
# Export (if needed) and evaluate v1 models on test + gold, plus the minimal-pair sign check on test.
#   scripts/train/eval_v1.sh <name>:<checkpoint_dir> ...   e.g. s32m_soup:checkpoints/s32m_soup
# Writes artifacts/<name>/, eval_reports/<name>_{test,gold}.{json,md}, eval_reports/pairs_<name>_test.json.
set -eu
cd "$(dirname "$0")/../.."
P=.venv/bin/python
L=checkpoints/logs
for spec in "$@"; do
  name=${spec%%:*}; ckpt=${spec#*:}
  [ -f artifacts/$name/model.int8.onnx ] || $P scripts/train/export.py --ckpt "$ckpt" --data-dir data \
    --out artifacts/$name > $L/export_$name.log 2>&1
  for S in test gold; do
    [ -f eval_reports/${name}_$S.json ] || $P scripts/eval/run_eval.py --profiler onnx:artifacts/$name --split $S \
      --out eval_reports/${name}_$S.json > $L/eval_${name}_$S.log 2>&1
  done
  [ -f eval_reports/pairs_${name}_test.json ] || $P scripts/train/pair_check.py --profiler onnx:artifacts/$name \
    --split test --out eval_reports/pairs_${name}_test.json > /dev/null 2>&1
  echo "evaluated $name"
done
