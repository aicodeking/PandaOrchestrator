#!/bin/sh
# Follow-up queue after run_v1.sh: retrain 32m seeds 1-2 with the shared head init (soup-compatible),
# then greedy soups for 32m and 68m.
set -eu
cd "$(dirname "$0")/../.."
P=.venv/bin/python
L=checkpoints/logs
T=checkpoints/cache/t400m_train.pt
while pgrep -f scripts/train/run_v1.sh > /dev/null; do sleep 30; done
for S in 1 2; do
  [ -f checkpoints/s32m_seed$S/train_summary.json ] || $P scripts/train/train.py --data-dir data \
    --out checkpoints/s32m_seed$S --epochs 10 --backbone jhu-clsp/ettin-encoder-32m --seed $S --distill-from $T \
    > $L/s32m_seed$S.log 2>&1
done
for B in 32m 68m; do
  [ -f checkpoints/s${B}_soup/soup.json ] || $P scripts/train/soup.py --runs checkpoints/s${B}_seed0 \
    checkpoints/s${B}_seed1 checkpoints/s${B}_seed2 --data-dir data --out checkpoints/s${B}_soup > $L/soup_$B.log 2>&1
done
echo done > $L/run_v1b.done
