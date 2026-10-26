# Panda Router v2: evaluated release

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
