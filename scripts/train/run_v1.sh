#!/bin/sh
# v1 GPU queue, run strictly sequentially (concurrent MPS jobs starve each other and swap).
# Assumes checkpoints/t400m is training or done (teacher: --max-len 256 --batch-size 32 --epochs 8).
set -eu
cd "$(dirname "$0")/../.."
P=.venv/bin/python
L=checkpoints/logs
T=checkpoints/cache/t400m_train.pt
mkdir -p $L
while [ ! -f checkpoints/t400m/train_summary.json ]; do sleep 30; done
[ -f $T ] || $P scripts/train/cache_teacher.py --teacher checkpoints/t400m/best --data-dir data --out $T > $L/cache.log 2>&1

run() {  # out_dir, then extra args
  out=$1; shift
  [ -f "$out/train_summary.json" ] || $P scripts/train/train.py --data-dir data --out "$out" --epochs 10 "$@" \
    > "$L/$(basename "$out").log" 2>&1
}
for S in 0 1 2; do run checkpoints/s32m_seed$S --backbone jhu-clsp/ettin-encoder-32m --seed $S --distill-from $T; done
run checkpoints/abl32m_direct --backbone jhu-clsp/ettin-encoder-32m --seed 0
run checkpoints/abl32m_regret0 --backbone jhu-clsp/ettin-encoder-32m --seed 0 --distill-from $T --regret-weight 0
run checkpoints/abl32m_pair0 --backbone jhu-clsp/ettin-encoder-32m --seed 0 --distill-from $T --pair-weight 0
run checkpoints/abl32m_anchor --backbone jhu-clsp/ettin-encoder-32m --seed 0 --distill-from $T \
  --anchors checkpoints/anchors_train.jsonl --anchor-weight 0.5
for S in 0 1 2; do run checkpoints/s68m_seed$S --backbone jhu-clsp/ettin-encoder-68m --seed $S --distill-from $T; done
run checkpoints/r150m --backbone jhu-clsp/ettin-encoder-150m --seed 0 --batch-size 16
for B in 32m 68m; do
  [ -f checkpoints/s${B}_soup/soup.json ] || $P scripts/train/soup.py --runs checkpoints/s${B}_seed0 \
    checkpoints/s${B}_seed1 checkpoints/s${B}_seed2 --data-dir data --out checkpoints/s${B}_soup > $L/soup_$B.log 2>&1
done
echo done > $L/run_v1.done
