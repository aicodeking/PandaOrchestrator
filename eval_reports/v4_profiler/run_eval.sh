#!/bin/sh
# usage: sh eval_reports/v4_profiler/run_eval.sh <name> <artifacts_dir>
set -u
cd "$(dirname "$0")/../.."
P=.venv/bin/python; R=eval_reports/v4_profiler; N=$1; A=$2
$P scripts/train/bench.py --artifacts $A --data-dir data > $R/bench_$N.log 2>&1
$P scripts/eval/run_eval.py --profiler onnx:$A --split gold --out $R/${N}_gold.json > /dev/null 2>&1
$P scripts/eval/run_eval.py --profiler onnx:$A --split test --out $R/${N}_test.json > /dev/null 2>&1
$P scripts/eval/outcome_eval.py --profiler onnx:$A --out $R/outcome_$N.json > /dev/null 2>&1
$P scripts/eval/attempt_eval.py --profiler onnx:$A --out $R/attempt_$N.json > /dev/null 2>&1
echo "done $N"
