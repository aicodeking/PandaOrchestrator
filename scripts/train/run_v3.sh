#!/bin/sh
# v3 MPS queue. Each stage is deliberately serial: concurrent MPS training starves both jobs.
#   prepare  build SWE and attempt-IRT anchors from the current v3 splits
#   sweep    32M direct anchor-weight sweep (0.3 / 1.0)
#   teacher  150M teacher at 512 tokens and a cache for distillation
#   distill  two 32M distilled seeds
#   soup     greedy soup + calibration of the two seeds
set -eu
cd "$(dirname "$0")/../.."

P=.venv/bin/python
L=checkpoints/logs
SWE=checkpoints/outcome_v3
ATT=checkpoints/attempt_outcome_v3/train.jsonl
SWE_TRAIN=$SWE/train.jsonl
SWE_VAL=$SWE/val.jsonl
CACHE=checkpoints/cache/v3_t150m_train.pt
REC=${REC:---anchor-weight 0.3 --regret-weight 0}
mkdir -p "$L"

prepare() {
  "$P" scripts/train/outcome_anchors.py --out "$SWE"
  "$P" scripts/train/attempt_anchors.py --out checkpoints/attempt_outcome_v3
}

run() {  # output dir, then train.py arguments
  out=$1
  shift
  if [ ! -f "$out/train_summary.json" ]; then
    "$P" scripts/train/train.py --data-dir data --out "$out" --epochs 8 --max-len 512 \
      --anchors "$ATT" --outcome-anchors "$SWE_TRAIN" --outcome-val "$SWE_VAL" "$@" \
      > "$L/$(basename "$out").log" 2>&1
  fi
}

case "${1:-sweep}" in
prepare)
  prepare
  ;;
sweep)
  prepare
  run checkpoints/v3_32_a03 --backbone jhu-clsp/ettin-encoder-32m --anchor-weight 0.3 --regret-weight 0
  run checkpoints/v3_32_a10 --backbone jhu-clsp/ettin-encoder-32m --anchor-weight 1.0 --regret-weight 0
  ;;
teacher)
  prepare
  # shellcheck disable=SC2086
  run checkpoints/v3_t150m --backbone jhu-clsp/ettin-encoder-150m --batch-size 16 --epochs 10 $REC
  if [ ! -f "$CACHE" ]; then
    "$P" scripts/train/cache_teacher.py --teacher checkpoints/v3_t150m/best --data-dir data --out "$CACHE" \
      --extra "$SWE_TRAIN" > "$L/cache_v3_t150m.log" 2>&1
  fi
  ;;
distill)
  prepare
  for seed in 0 1; do
    # shellcheck disable=SC2086
    run "checkpoints/v3_s32m_seed$seed" --backbone jhu-clsp/ettin-encoder-32m --seed "$seed" \
      --distill-from "$CACHE" $REC
  done
  ;;
soup)
  "$P" scripts/train/soup.py --runs checkpoints/v3_s32m_seed0 checkpoints/v3_s32m_seed1 --data-dir data \
    --out checkpoints/v3_s32m_soup > "$L/v3_s32m_soup.log" 2>&1
  ;;
*)
  echo "usage: $0 {prepare|sweep|teacher|distill|soup}" >&2
  exit 2
  ;;
esac
