# Panda Router v1: results

## What ships

`artifacts/panda-router-v1/` is a task profiler fine-tuned from **Ettin-32M** (MIT licence).

- Size: **31 MB** int8 ONNX (122 MB fp32).
- Training: 3 seeds trained by copying the outputs of a 400M teacher model (distillation). The
  greedy weight average kept only the best seed (seed 1). Each output has its own calibration
  temperature, fitted on the validation split.
- Pipeline: the profiler reads a task and returns a `TaskProfile` (category, difficulty 1–10, ten
  required skill levels, flags, checklist answers, output-token quantiles). The deterministic
  matcher (`panda_router/matcher`) then scores every model card with uncertainty-aware MIRT
  (multidimensional item response theory) and picks a model under the requested policy.

Run it:

- `./pandacode-run.sh` starts the HTTP API on :8765.
- `.venv/bin/python -m panda_router.serve.cli route --task "..." --artifacts artifacts/panda-router-v1`
  routes a single task from the command line.

When `--artifacts` is given and the model fails to load, the router now **raises an error** instead
of silently falling back to the heuristic. The response field `router.profiler` names the profiler
that was used.

## Data

| Set | Size | Source |
|---|---|---|
| train / val / test | 3,314 / 279 / 300 | 2,807 originals, 63% real (SWE-rebench, SWE-smith, WildChat), the rest synthetic from a seed grid with personas. Plus 1,086 minimal pairs. Split by embedding cluster. |
| gold (test only) | 285 real tasks | A separate sha1 partition, never used for training or model selection. Each task has at least 2 teachers. |

- **Teachers:** Codex `gpt-5.6-luna` and Grok `grok-4.7-build-fast`. Local `gemma4:26b` broke ties
  on training data and was the second teacher for gold. Kimi hit its quota almost immediately.
- **Agreement between teachers:** category 0.87, difficulty Spearman 0.89, flags κ 0.82. See
  `data/STATS.md` and `data/gold/README.md`.

## Profiler quality

Full tables: `eval_reports/compare_v1.md`. Latency is batch-1 int8 on CPU.

| Model | Gold category acc | Gold difficulty MAE | Gold difficulty ρ | Gold flag AUROC | Test category acc | Test difficulty MAE | Size | CPU p50 |
|---|---|---|---|---|---|---|---|---|
| heuristic | 0.498 | 1.34 | 0.57 | 0.64 | 0.531 | 1.49 | n/a | 0.6 ms |
| kNN (Ettin-32M embeddings) | 0.579 | 1.10 | 0.49 | 0.71 | 0.470 | 1.11 | n/a | 37 ms |
| Ettin-400M teacher | 0.642 | **0.74** | **0.80** | 0.87 | 0.720 | 0.86 | 1.5 GB | ~166 ms |
| Ettin-150M direct | **0.667** | 0.83 | 0.75 | 0.87 | **0.753** | **0.79** | 459 MB† | ~29 ms |
| Ettin-68M distilled | 0.628 | 0.87 | 0.72 | 0.86 | 0.693 | 0.86 | ~70 MB | ~25 ms* |
| **Ettin-32M distilled (v1)** | 0.614 | 0.84 | 0.72 | 0.85 | 0.680 | 0.83 | **31 MB** | **12.8 ms** (p95 25.8) |

- **Every trained model clearly beats both baselines** on all profiler metrics, on both test and
  gold. Calibration error is also low for v1: difficulty ECE 0.047, flags 0.041, checklist 0.044.
- `*` These latencies were measured while training was running. v1 was re-benchmarked on an idle
  machine; at 512 tokens it takes 27 ms.
- `†` The 150M model fails the 1-point int8 tolerance, so it would ship nearly fp32-sized. That is
  why v1 is the 32M model.
- **Minimal-pair check** (test set, 151 checks; does the predicted change go the expected way?):
  v1 **100%**, heuristic 68%.

## Routing quality (gold, 50 random card pools per task)

Utility regret only makes sense in `max_utility` mode (review finding), so routing is reported per
mode: `eval_reports/routing_max_utility_gold.md`. The `fixed_average` row returns the same mean
profile for every task and is the floor any profiler must beat.

| Profiler | max_utility pick agreement | max_utility regret | cheapest-mode pick agreement | cheapest cost ratio |
|---|---|---|---|---|
| fixed_average (floor) | 0.791 | 0.0060 | 0.445 | 1.106 |
| heuristic | 0.818 | 0.0060 | 0.703 | 0.342 (too cheap: 27% of picks fall below min P) |
| kNN | 0.838 | 0.0043 | 0.677 | 0.721 |
| Ettin-400M | 0.889 | 0.0022 | 0.790 | 0.819 |
| **v1 (32M)** | 0.882 | 0.0025 | 0.763 | 0.668 |

Against the teacher-label oracle, v1 roughly halves regret compared with the heuristic and the floor.

## Ablations (32M, single seed, val-selected)

| Variant | Gold category | Gold difficulty MAE | max_utility regret | Minimal-pair sign |
|---|---|---|---|---|
| default (distilled + pair loss + regret loss) | 0.600–0.614 | 0.84–0.88 | 0.0025 | 100% |
| no regret loss | 0.628 | 0.85 | 0.0026 | 100% |
| no pair loss | 0.607 | 0.86 | 0.0028 | 96% |
| no distillation (direct) | 0.604 | 0.86 | 0.0029 | 99% |
| + outcome-anchor auxiliary loss | 0.604 | 0.88 | 0.0030 | n/a |

The effects are small, within seed noise of about ±0.015 on category.

- **Pair loss:** clearly helps consistency on the minimal-pair edits.
- **Regret loss:** no measurable gain.
- **Outcome-anchor loss:** raised gold Spearman against real-outcome difficulty slightly (0.13 vs
  0.04–0.14) but hurt routing, so it is not shipped.
- **Distillation:** the 400M teacher had to run at 256 tokens on MPS. Distilling from it was not
  better than training directly.

## Example routes (v1, default policy `cheapest_above_threshold`, all 17 cards)

| Task | Profile | Pick |
|---|---|---|
| "What does HTTP status 418 mean?" | chat_simple, d=1 | local gemma4:26b (P 0.97) |
| Raft KV store loses data after leader re-election; fix and add a test | bugfix, d=7, multi_file, needs_review | grok-4.6 (P 0.78) |
| Settings page from Figma screenshot, React + Tailwind | ui_frontend, d=4, needs_vision | gpt-6-luna (P 0.94) |
| 200k-token outage log; find the trigger and write a timeline | research, d=6, long_context | gpt-6-luna (P 0.79) |
| Vector DB research report with cited benchmarks | research, d=6, ambiguous_spec | grok-4.6 (P 0.84) |

Two errors are visible here. The Raft task should set `needs_tools`. The log task would fit better
as data_analysis or debugging.

## Limitations (read before trusting it)

1. **Labels come from teacher LLMs, not real outcomes.** On 92 gold SWE tasks, teacher difficulty
   had Spearman ≈ 0 with IRT difficulty fitted on public per-instance agent outcomes. The anchor
   ladder is weak: older open models, and 54% of those tasks failed in every run. Even so,
   **difficulty on real coding tasks is unvalidated.** The fix is to log real `RouteOutcome`s and
   refit difficulty and card θ from them.
2. **Model cards are estimates.** Skill θ values come from public benchmarks or are marked
   `estimated` with a wider se. Routing can only be as good as the cards.
3. **Gold is small (285 tasks) and skewed toward bugfixes.** 205 gold rows used gemma rather than
   Grok as the second teacher, so gold slightly measures agreement with a different teacher mix.
   One WildChat prompt text appears in both gold and train.
4. **Context features leak on real SWE rows.** `files_in_scope` and `estimated_input_tokens` were
   taken from the reference patch, so they correlate 0.92 with `multi_file`. In real use these are
   estimates. Retrain with these features derived from the issue text, or dropped, or noised.
5. The loss normaliser uses the first batch, which is noisy for the sparse losses. The soft matcher
   used for the regret loss trains only `max_utility`, while serving defaults to cheapest mode.
6. P(success) runs about 1–2 points high compared with Monte Carlo (delta-method approximation).

## Next steps

1. Fix the context-feature leak (4) and relabel gold with Codex + Grok once quotas allow, then
   retrain. The pipeline is resumable: `panda_router/train/README.md` for training,
   `scripts/datagen/run.py` for data.
2. Add more data: about 4,100 generated tasks are waiting for a second teacher.
3. Deploy, log outcomes, and update card θ online (PLAN §12.4 #5). This is the only path to
   outcome-grounded routing.
4. Optional: try a 68M model distilled from the 150M model trained at 512 tokens. That run was
   started but stopped because MPS throughput collapsed.
