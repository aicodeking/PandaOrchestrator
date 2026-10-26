#!/bin/sh
# v2 GPU queue (strictly sequential: concurrent MPS jobs starve each other). Stage given as $1:
#   sweep   - 32M direct runs on data v2: anchor weight x regret mode
#   teacher - 150M direct at 512 tokens with the chosen recipe ($REC), then teacher cache incl. anchor rows
#   distill - 68M and 32M students distilled from the 150M cache
# Data: data/{train,val}.jsonl (v2) + checkpoints/outcome/{train,val}.jsonl (scripts/train/outcome_anchors.py).
set -eu
cd "$(dirname "$0")/../.."
P=.venv/bin/python
L=checkpoints/logs
OA=checkpoints/outcome/train.jsonl
OV=checkpoints/outcome/val.jsonl
T=checkpoints/cache/v2_t150m_train.pt
mkdir -p $L
REC=${REC:---anchor-weight 0.3 --regret-weight 0}  # chosen by the 32M sweep (README / RESULTS.md)

run() {  # out_dir, then extra args
  out=$1; shift
  [ -f "$out/train_summary.json" ] || $P scripts/train/train.py --data-dir data --out "$out" --epochs 8 \
    --outcome-anchors $OA --outcome-val $OV "$@" > "$L/$(basename "$out").log" 2>&1
}
B32=jhu-clsp/ettin-encoder-32m
case "${1:-sweep}" in
sweep)
  run checkpoints/v2_32_base --backbone $B32 --anchor-weight 0 --regret-mode max_utility
  run checkpoints/v2_32_a1c --backbone $B32 --anchor-weight 1.0 --regret-mode cheapest
  # anchor 3.0 was stopped after epoch 4: val_score 2 points below anchor 1.0 and no outcome-val gain
  [ -d checkpoints/v2_32_a3c_killed ] || run checkpoints/v2_32_a3c --backbone $B32 --anchor-weight 3.0 --regret-mode cheapest
  run checkpoints/v2_32_a1r0 --backbone $B32 --anchor-weight 1.0 --regret-weight 0
  ;;
sweep2)  # anchors at weight 1 transfer weakly to unseen repos and cost gold MAE: lower weight / repo-centred targets
  run checkpoints/v2_32_a03c --backbone $B32 --anchor-weight 0.3 --regret-mode cheapest
  OA=checkpoints/outcome_rc/train.jsonl OV=checkpoints/outcome_rc/val.jsonl \
    run checkpoints/v2_32_rc1c --backbone $B32 --anchor-weight 1.0 --regret-mode cheapest
  ;;
teacher)
  # shellcheck disable=SC2086
  run checkpoints/v2_t150m --backbone jhu-clsp/ettin-encoder-150m --batch-size 16 --epochs 10 $REC
  [ -f $T ] || $P scripts/train/cache_teacher.py --teacher checkpoints/v2_t150m/best --data-dir data --out $T \
    --extra $OA > $L/cache_v2.log 2>&1
  ;;
distill)
  # shellcheck disable=SC2086
  run checkpoints/v2_s68m --backbone jhu-clsp/ettin-encoder-68m --distill-from $T $REC
  # shellcheck disable=SC2086
  run checkpoints/v2_s32m --backbone $B32 --distill-from $T $REC
  ;;
esac
echo "done $1" >> $L/run_v2.done
