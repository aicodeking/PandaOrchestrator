#!/bin/sh
# Iteration after run_v1c.sh: the 400m teacher had to run at max_len 256 (MPS memory/throughput), and
# 150m trained directly at 512 beat it on val (89.3 vs 87.6). Distil 32m from the 150m instead.
set -eu
cd "$(dirname "$0")/../.."
P=.venv/bin/python
L=checkpoints/logs
T=checkpoints/cache/r150m_train.pt
while [ ! -f $L/run_v1c.done ]; do sleep 30; done
[ -f $T ] || $P scripts/train/cache_teacher.py --teacher checkpoints/r150m/best --data-dir data --out $T > $L/cache150.log 2>&1
for S in 0 1 2; do
  [ -f checkpoints/s32m150_seed$S/train_summary.json ] || $P scripts/train/train.py --data-dir data \
    --out checkpoints/s32m150_seed$S --epochs 10 --backbone jhu-clsp/ettin-encoder-32m --seed $S --distill-from $T \
    > $L/s32m150_seed$S.log 2>&1
done
[ -f checkpoints/s32m150_soup/soup.json ] || $P scripts/train/soup.py --runs checkpoints/s32m150_seed0 \
  checkpoints/s32m150_seed1 checkpoints/s32m150_seed2 --data-dir data --out checkpoints/s32m150_soup > $L/soup_32m150.log 2>&1
echo done > $L/run_v1d.done
