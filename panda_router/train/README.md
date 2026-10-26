# Profiler training pipeline

Ettin encoder (ModernBERT) + heads: category (13, soft CE), difficulty (CORN, 10 levels),
10 skill axes (CORN, 11 levels), flags (7, BCE), checklist (24, BCE), out_tokens_log10 p10/p50/p90
(pinball). Each head loss is divided by its first value. Extra losses:
- minimal pairs (`--pair-weight`): a margin ranking loss on the edited-vs-original deltas
- decision-focused regret (`--regret-weight`): `panda_router/model/soft_matcher.py`, which mirrors
  `panda_router/matcher/core.py`
- distillation (`--distill-from`): KL at T per head, plus the soft-label loss

Set a weight to 0 to ablate that loss. Input text always comes from `panda_router.text.format_input`.

Code: `panda_router/model/` (net, corn, losses, soft_matcher, decode, onnx_profiler) and
`panda_router/train/` (data, trainer, metrics, distill, soup, calibrate, export, fake_data).

## Exact sequence (real data in `data/{train,val,test}.jsonl`)

```sh
P=.venv/bin/python
# 1. teacher 400m
$P scripts/train/train.py --backbone jhu-clsp/ettin-encoder-400m --data-dir data --out checkpoints/t400m --epochs 6 --seed 0
# 2. cache teacher outputs for train once
$P scripts/train/cache_teacher.py --teacher checkpoints/t400m/best --data-dir data --out checkpoints/cache/t400m_train.pt
# 3. students 68m and 32m x 3 seeds, distilled
for B in 68m 32m; do for S in 0 1 2; do
  $P scripts/train/train.py --backbone jhu-clsp/ettin-encoder-$B --data-dir data --out checkpoints/s${B}_seed$S \
     --epochs 6 --seed $S --distill-from checkpoints/cache/t400m_train.pt
done; done
# 4+5. greedy soup per backbone, then per-head temperature calibration on val (writes heads.json)
for B in 68m 32m; do
  $P scripts/train/soup.py --runs checkpoints/s${B}_seed0 checkpoints/s${B}_seed1 checkpoints/s${B}_seed2 \
     --data-dir data --out checkpoints/s${B}_soup
done
#    (re-calibrate only: $P scripts/train/calibrate.py --ckpt checkpoints/s32m_soup --data-dir data)
# 6. export fp32 + int8 ONNX, compare heads, write artifacts/<name>/
$P scripts/train/export.py --ckpt checkpoints/s32m_soup --data-dir data --out artifacts/profiler-32m
$P scripts/train/export.py --ckpt checkpoints/s68m_soup --data-dir data --out artifacts/profiler-68m
# 7. CPU latency at batch 1 (merged into metrics.json)
$P scripts/train/bench.py --artifacts artifacts/profiler-32m --data-dir data
```

## v2 sequence (data v2 + outcome anchors), `scripts/train/run_v2.sh`

```sh
$P scripts/train/outcome_anchors.py            # checkpoints/outcome/{train,val,heldout}.jsonl (repo-held-out split)
sh scripts/train/run_v2.sh sweep               # 32M: anchor weight x regret mode (sweep2: weight 0.3, repo-centred)
sh scripts/train/run_v2.sh teacher             # 150M direct, 512 tokens, then teacher cache incl. anchor rows
sh scripts/train/run_v2.sh distill             # 68M / 32M students from the 150M cache
$P scripts/train/export.py --ckpt checkpoints/v2_t150m/best --data-dir data --out artifacts/<name> --per-channel
$P scripts/eval/outcome_eval.py --profiler onnx:artifacts/<name> --out eval_reports/v2/outcome_<name>.json
$P scripts/eval/hard_tasks.py --profilers onnx:artifacts/panda-router-v1 onnx:artifacts/<name> --out eval_reports/v2/hard_tasks.md
```

- Outcome-anchor rows (`--outcome-anchors`, needs `--anchor-weight > 0`) have no teacher labels: their label and
  distillation losses are masked (`w = 0`) and they train the difficulty head only, through a smooth-L1 anchor loss
  weighted by outcome trust `clip((0.5/se)^2, 0.05, 1)`. `--outcome-val` logs held-out-task Spearman per epoch.
- `--regret-mode cheapest` trains a smooth `cheapest_above_threshold` objective (`soft_matcher.cheapest_score`).
- `--per-channel` int8 lets the 150M pass the 1-point tolerance at stage 0 (per-tensor did not, at any stage).

Ablations: pass `--regret-weight 0` and/or `--pair-weight 0` and compare `val_score` in
`train_summary.json`. Run the gold-set eval to decide what to keep.

Serving:

```python
from panda_router.model.onnx_profiler import OnnxProfiler
OnnxProfiler("artifacts/panda-router-v2").profile(task)  # -> TaskProfile
```

`TorchProfiler(checkpoint_dir)` loads a checkpoint directory instead of ONNX artifacts.

## Details

- Batches use a single fixed length bucket (64/128/256/512) to avoid the MPS SDPA leak. The
  pair-aware sampler never splits an original from its minimal-pair edits.
- The backbone runs under bf16 autocast. Pooling, heads and losses run in fp32. Optimiser: AdamW
  with 6% warmup and linear decay, grad clip 1.0.
- Default LR by backbone size: 1e-4 for 32m and smaller, 5e-5 for 68m–150m, 3e-5 for 400m.
- `val_score` is the mean of the per-head primary metrics on a 0–100 scale. It drives early
  stopping, the soup and the int8 check. The primary metrics are:
  - category: accuracy
  - difficulty: 1 − MAE/9
  - skills: 1 − MAE/10
  - flags: F1
  - checklist: F1
  - out_tokens: 1 − MAE/4
- Checkpoint directory contents: `model.safetensors`, backbone `config.json`, tokenizer files,
  `profiler_config.json`, `heads.json` (temperatures, label order, taxonomy version) and
  `val_metrics.json`.
- Export uses the TorchScript ONNX exporter (`dynamo=False`) with `torch.compile` disabled. Batch
  and sequence axes are dynamic, opset 17, eager attention. int8 uses ORT `quantize_dynamic` and is
  applied in stages:
  1. quantise everything
  2. keep the head Gemms in fp32
  3. also keep the last k encoder layers in fp32, raising k until no head drops more than 1 point
  The chosen exclusions go in `heads.json`; the drops go in `metrics.json`.
- Fake data, for pipeline tests only: `$P -m panda_router.train.fake_data --out checkpoints/fake`.
  Never ship a model trained on it.
- Throughput: `$P scripts/train/throughput.py --backbones 32m 68m 150m 400m --seq 256`.
