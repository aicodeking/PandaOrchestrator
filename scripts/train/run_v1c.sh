#!/bin/sh
# Extra variant after run_v1b.sh: distilled 32m at max_len 256 (the teacher's length; ~2x cheaper inference).
set -eu
cd "$(dirname "$0")/../.."
P=.venv/bin/python
L=checkpoints/logs
T=checkpoints/cache/t400m_train.pt
while [ ! -f $L/run_v1b.done ]; do sleep 30; done
for S in ${SEEDS:-0}; do
  [ -f checkpoints/s32m256_seed$S/train_summary.json ] || $P scripts/train/train.py --data-dir data \
    --out checkpoints/s32m256_seed$S --epochs 10 --backbone jhu-clsp/ettin-encoder-32m --seed $S --max-len 256 \
    --distill-from $T > $L/s32m256_seed$S.log 2>&1
done
echo done > $L/run_v1c.done
