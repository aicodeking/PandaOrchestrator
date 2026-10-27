# Panda Router v4

v4.3 (2026-10-27): `/escalate` never offers a model weaker than one that already failed (the user's over-estimate
rule). The ladder numbers are unchanged; escalating from `choice` improved to 90.7 within 2 attempts. Gold eval:
`eval_reports/v4/gold_v43.json`. v4.2 fixed the policy modes (see `eval_reports/v4/REPORT.md`).

**Shipped:** `artifacts/panda-router-v4` = 32M profiler (distilled from a 150M teacher trained on Modal, asymmetric
"over-estimate" difficulty loss, fine-tuned on 1,474 vague-request examples) + a learned per-model success head
(`success_head.json`) + a safer policy. Modal spend: $1.67 of the $30 budget.

| on 150 held-out real attempt tasks, 9-model pool | success / 100 | $ / 100 |
|---|---:|---:|
| v4 single pick, max_utility (default) | 77.3 | 0.99 |
| v4 single pick, max_quality | 82.0 | 1.20 |
| v4 single pick, cheapest_above_threshold | 74.0 | 0.74 |
| v4 escalate from `choice`, <= 2 attempts (v4.3: never steps down) | 90.7 | 1.68 |
| v4 ladder, <= 2 attempts | 88.7 [83.3, 93.3] | 0.88 |
| v4 ladder, <= 3 attempts | 92.0 | 1.23 |
| v3 single pick (max_utility) | 66.7 | 0.23 |
| always gpt-6.1-sol | 79.3 | 1.11 |
| oracle | 94.0 | 0.56 |

- 85 is reached with one retry along `escalation_ladder` (needs a failure signal), not single-shot.
- $0 picks in cheapest mode, full pool: 88% -> 0%. Under-estimation (picked model failed, a stronger affordable one
  passed): 26.7% (v3) -> 14.0%; over-spend 58% -> 69%, the trade the user asked for.
- `p_success` is calibrated per model (train/val ECE 0.015; gold ECE 0.375 -> 0.127); decisions use
  `p_success_lower`. Trivial-task P is understated (~0.5) for lack of trivial outcome data.
- Outcome data: 9 attempters (5 OpenRouter until credits ran out; Claude Haiku/Sonnet/Opus and GPT-6-Luna via
  subscription CLIs), judges ds-think > dsh > codex-terra (parity kappa 0.68-0.85). The DeepSeek (dsh) balance also
  ran out mid-grading. Claude CLI thinking could not be capped, which favours the Claude models.
- Details: `eval_reports/v4/REPORT.md`, `eval_reports/v4_profiler/REPORT.md`, `data/outcomes/REPORT_v4_attempts.md`,
  `data/vague_v4/STATS.md`.

---

# Panda Router v3 (superseded by v4)

## What changed

- **Teacher:** DeepSeek V4.1 Flash (OpenRouter, $2.77 for 8,074 labels) labels every training and gold row;
  data grew from 4,895 to 8,247 rows, 100% with >= 2 teachers. Gold: 359 rows, Codex + DeepSeek on all.
- **Real outcomes, attempt-and-grade:** 999 train/val + 150 gold tasks attempted by five OpenRouter models and
  graded by DeepSeek V4.1 Flash with thinking (kappa 0.85 vs Kimi K3.1 Pro). Stopped at $44.55 when the
  account ran out of credits: 511 train/val tasks and 140 gold tasks have graded outcomes. Cards adjusted from
  the fit: minimax-m3.1-flash and gemini-3.8-flash down on several axes, gpt-6.1-sol planning up,
  deepseek-v4.1-flash +1.4 on all axes (passed 68% of gold tasks vs qwen3.8-flash 47%, but its card ranked it
  below qwen). `data/outcomes/REPORT_attempts.md`.
- **Profiler:** direct Ettin-32M (`checkpoints/v3_32_a03`, outcome-anchor weight 0.3). The planned 150M teacher
  + distillation was dropped: the host was too loaded (~9 ex/s). Weight 1.0 was worse (ablation a10).
- **Matcher:** default mode is now `max_utility`. Outcome calibration of P(success) is implemented but opt-in.

## Real routed success (140 gold tasks, pool = the five attempters)

| policy | success / 100 | $ / 100 |
|---|---:|---:|
| always cheapest | 47.1 | 0.064 |
| v2, cheapest_above_threshold (old default) | 50.0 | 0.095 |
| v3, cheapest_above_threshold | 51.4 | 0.142 |
| **v3, max_utility (new default)** | **67.9** | **0.156** |
| v3, any mode with calibration on (default min_p) | 78.6 | 1.061 |
| always strongest | 78.6 | 1.061 |
| oracle | 90.0 | 0.192 |

Calibration (`data/outcomes/REPORT_calibration.md`) cuts gold ECE from 0.33 to 0.13, but the calibrated
probabilities are low enough that every threshold policy at min_p >= 0.7 picks the strongest model; at lower
thresholds it never beat a mix of always-cheapest and always-strongest. So it is shipped off
(`PANDA_ROUTER_CALIBRATION=on` to enable). The card fix plus `max_utility` is what moved success from 50 to 68.

## Profiler quality (gold, 359 tasks)

| model | category | difficulty MAE / rho | flags AUROC | attempt-IRT rho | SWE held-out rho | max-utility regret | hard tasks |
|---|---:|---:|---:|---:|---:|---:|---:|
| v1 | 0.624 | 0.900 / 0.675 | 0.885 | 0.178 | 0.025 | 0.0025 | 0.80 |
| v2 | 0.641 | 0.897 / 0.705 | 0.886 | 0.115 | 0.119 | 0.0022 | 0.85 |
| **v3** | **0.688** | **0.825 / 0.747** | **0.901** | **0.212** | 0.081 | **0.0021** | 0.85 |
| v3 a10 (anchor 1.0) | 0.652 | 1.032 / 0.549 | 0.890 | 0.164 | 0.117 | 0.0028 | 0.90 |

v3 beats v2 on every gold head and on attempt-outcome correlation; it is lower on SWE held-out rho (both weak).
Full tables: `eval_reports/compare_v3.md`. Same 32M architecture and int8 size (31 MB) as v2.

## Next steps

1. Top up OpenRouter (~$5) and finish grading the ~2,170 pending answers (`REPORT_attempts.md` has the
   commands), then refit cards from all attempts: the calibration report shows refitted card thetas alone take
   `max_utility` to 68.6 at $0.185 on the five-model pool, and they generalise to any pool.
2. Extend attempt-and-grade to agentic coding with the models you actually route to.
3. Train the 150M teacher + distilled 32M on an idle machine.

---

# Panda Router v2: evaluated release (superseded by v3)

## Ship decision

`artifacts/panda-router-v2/` ships the **Ettin-32M student distilled from the v2 150M teacher**
(`checkpoints/v2_s32m`, ONNX int8, 31 MB; package 157 MB incl. fp32 fallback). `pandacode-run.sh`
serves it on port 8765. The training worker first shipped the direct 32M; the architect switched to
the distilled student on review because it is better on what the router is for:

- **routing:** lowest max-utility regret of any shippable model (0.0017 vs v1 0.0019, direct 0.0020)
  and the cheapest cheapest-mode picks (cost ratio 0.660 vs v1 0.784);
- **real outcomes:** held-out SWE-bench IRT Spearman 0.119 (within-repo 0.143) vs v1 0.025 / 0.063;
- **hard tasks:** 0.85 pass rate, the only small model that rates lock-free MPMC >= 7;
- **fresh test:** category 0.683 vs v1 0.642; flags AUROC 0.839 on gold vs v1 0.769.

Trade-off, stated plainly: on gold it only **ties v1 on category accuracy (0.623)** and its
difficulty MAE is 0.02 worse (0.904 vs 0.882). The direct 32M (`artifacts/v2_32_base_onnx`) is the
better pure profiler on gold (0.660 / 0.877) but routes worse. The 150M teacher is best on almost
everything but runs ~4.4x slower than the 32M (55-83 ms p50 under load, est. ~55 ms idle), over the
30 ms budget.

| model | gold category | gold difficulty MAE | held-out / within-repo outcome rho | max-utility regret | int8 MB | CPU p50 / p95 ms | result |
|---|---:|---:|---:|---:|---:|---:|---|
| v1 | 0.623 | 0.882 | 0.025 / 0.063 | 0.00190 | 30.9 | — | baseline |
| v2 direct 32M | **0.660** | **0.877** | 0.100 / 0.108 | 0.00200 | 31.0 | 18.21 / 66.93 | better profiler, worse routing |
| **v2 distilled 32M (ship)** | 0.623 | 0.904 | 0.119 / **0.143** | **0.00171** | 31.0 | 9.64 / 18.63 | **shipped** |
| v2 distilled 68M | 0.647 | 0.941 | **0.139** / 0.153 | 0.00206 | 66.2 | 21.58 / 41.82 | MAE and regret regressions |
| v2 direct 150M teacher | 0.675 | 0.867 | 0.139 / 0.146 | 0.00153 | 143.9 | 55.43 / 130.19 | too slow |

Latency is `scripts/train/bench.py --n 300`, batch 1, int8, on the shared
host. The host was actively busy with unrelated processes, so these are not
claimed as idle-machine measurements; the shipped model still measured below
30 ms p50 under that contention. The route CLI also loaded
`OnnxProfiler(panda-router-v2/model.int8.onnx)` successfully.

## Evaluation

Full, reproducible tables are in `eval_reports/compare_v2.md`.

| routing mode / model | v1 | v2 ship (distilled 32M) | v2 direct 32M | fixed-average floor |
|---|---:|---:|---:|---:|
| max-utility regret (lower is better) | 0.00190 | **0.00171** | 0.00200 | 0.00710 |
| cheapest cost ratio (lower is cheaper) | 0.784 | **0.660** | 0.739 | 2.111 |
| cheapest `P(success) < 0.75` | **0.197** | 0.233 | 0.232 | 0.043 |

v2 buys cheaper models more often; about 23% of its cheapest-mode picks fall under 0.75 P(success)
by the teacher-label oracle (v1 20%). Raise `min_p_success` if you want v1-like caution.

The hard-task check gives the shipped (distilled) model 7.2 for lock-free MPMC Rust (target 7–10;
pass) and 1.6 for HTTP 418 (target 1–2; pass); the direct 32M gives 6.1 / 1.5.

## Ablations

The sweep used the 32M direct backbone before the 150M teacher and students.
Gold values below are torch checkpoint evaluations; outcome rho is held-out
issue Spearman.

| variant | anchors / regret | gold category | gold MAE | outcome rho | max-utility regret |
|---|---|---:|---:|---:|---:|
| base | none / 0.05 | **0.657** | **0.878** | 0.104 | 0.00193 |
| a1c | weight 1.0, cheapest / 0.05 | 0.638 | 0.934 | 0.132 | 0.00227 |
| a1r0 | weight 1.0, max-utility / 0 | 0.641 | 0.924 | 0.122 | 0.00210 |
| a03c | weight 0.3, cheapest / 0.05 | 0.635 | 0.911 | 0.124 | **0.00181** |
| rc1c | repo-centred weight 1.0, cheapest / 0.05 | 0.647 | 0.929 | 0.101 | 0.00207 |

Outcome anchors improved outcome correlation but hurt gold MAE. The selected
teacher/student recipe used anchor weight 0.3 and regret weight 0 because the
cheapest-mode regret objective did not improve the sweep. Distillation improved
routing regret and outcome correlation for the 32M student, but reduced gold
category accuracy and increased MAE relative to the direct base; it was not a
release win.

## Limitations

1. Gold-label composition is mixed: 205 rows use Codex+Gemma and 45 use
   Codex+DeepSeek. The 700 hard tasks are Codex-only.
2. SWE-bench outcome offsets are weak, so held-out outcome correlation is a
   useful but limited validation target rather than a direct success estimate.
3. The package deliberately keeps both int8 and fp32 ONNX files. Serving
   selects int8 by default; the package-size result includes both.
4. No candidate met every strict criterion, notably the shipped model's tiny
   routing-regret regression and its lock-free MPMC hard-task miss.

## Run

```sh
./pandacode-run.sh
.venv/bin/python -m panda_router.serve.cli route \
  --artifacts artifacts/panda-router-v2 --profile \
  --task 'Design a lock-free MPMC queue in Rust and prove it is linearizable.'
```
