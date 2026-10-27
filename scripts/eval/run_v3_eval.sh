#!/bin/sh
# v3 evaluation queue: one heavy job at a time. Usage: sh scripts/eval/run_v3_eval.sh <name> <artifacts_dir>
set -eu
cd "$(dirname "$0")/../.."
P=.venv/bin/python; R=eval_reports/v3; N=$1; A=$2
$P scripts/eval/run_eval.py --profiler onnx:$A --split gold --out $R/${N}_gold.json > /dev/null
$P scripts/eval/run_eval.py --profiler onnx:$A --split test --out $R/${N}_test.json > /dev/null
$P scripts/eval/run_eval.py --profiler onnx:$A --split test --data checkpoints/test_fresh_v2.jsonl --out $R/${N}_testfresh.json > /dev/null
$P scripts/eval/outcome_eval.py --profiler onnx:$A --out $R/outcome_$N.json > /dev/null
$P scripts/eval/attempt_eval.py --profiler onnx:$A --out $R/attempt_$N.json > /dev/null
PANDA_ROUTER_CALIBRATION=off $P scripts/eval/attempt_eval.py --profiler onnx:$A --out $R/attempt_${N}_nocal.json > /dev/null
echo "done $N"
