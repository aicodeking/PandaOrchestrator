# v4 profiler candidates (Modal-trained) vs v3

Recipe: v3 data + anchors (attempt-IRT, SWE outcome), anchor weight 0.3, regret 0, 512 tokens, bf16, **new `--under-w 2.5`**
(difficulty under-prediction penalised 2.5x: weighted CORN positives + asymmetric anchor smooth-L1; default 1.0 elsewhere).
Teachers on L40S: 150M 10 ep (val 88.81, outcome-val rho 0.264, 8 min), 400M 8 ep (val 89.44, rho 0.231, 15 min).
Both cached; 3 seeds of 32M distilled from each (8 ep, ~2 min each), greedy soup (it kept the single best seed both times), plus one 68M per teacher.
Pilot (150 steps of 150M): L40S 47 s vs A100-40GB 66 s -> L40S used throughout (faster and cheaper).
Export: int8 per-channel ONNX. Latency = CPU batch 1, p50, short inputs, Mac under load (v3 re-benched on a copy, same conditions).
v3 attempt column uses `attempt_v3_caloff` (calibration off, max_utility), the like-for-like policy.
bias = mean(pred) - mean(label) on difficulty (positive = over-estimates).

| candidate | val int8 | MB | p50 ms | gold cat acc | gold diff rho | gold diff bias | test diff rho | test diff bias | outcome rho | attempt rho | max_util succ/100 | cost/100 $ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v3 (baseline) | 87.11 | 33 | 8.2 | 0.688 | 0.747 | -0.14 | 0.885 | -0.07 | 0.081 | 0.212 | 67.9 | 0.156 |
| t150m_s32m_soup | 86.91 | 33 | 9.5 | 0.682 | 0.721 | 0.12 | 0.894 | 0.02 | 0.112 | 0.137 | 65.3 | 0.166 |
| t400m_s32m_soup | 87.01 | 33 | 10.8 | 0.657 | 0.711 | 0.05 | 0.893 | 0.02 | 0.091 | 0.172 | 65.3 | 0.160 |
| t150m_s68m_seed0 | 87.39 | 69 | 19.1 | 0.685 | 0.729 | 0.05 | 0.877 | 0.06 | 0.119 | 0.262 | 65.3 | 0.152 |
| t400m_s68m_seed0 | 86.93 | 69 | 23.1 | 0.688 | 0.728 | 0.12 | 0.881 | 0.09 | 0.156 | 0.235 | 66.0 | 0.170 |

Modal total: $1.60 over 16 jobs (cap $15).

Hard-task probe (pass rate): v3 0.85, t150m_s32m 0.95, t400m_s32m 0.90, t150m_s68m 0.95, t400m_s68m 0.90 (`hard_tasks.md`).

## Reading
- Over-estimate goal met: gold difficulty bias moved from -0.14 (v3) to +0.05..+0.12; test bias -0.07 -> +0.02..+0.09; hard-task pass 0.85 -> 0.90-0.95.
- Cost: gold difficulty rho dropped (0.747 -> 0.71-0.73); test rho ~equal for 32M (0.89), lower for 68M. Category acc ~equal.
- Outcome rho (SWE heldout) up for all (0.081 -> 0.09-0.16); attempt-IRT rho: only 68M (0.235-0.262) beats v3 (0.212); max_utility success is 65-66/100 vs v3 67.9 (cost 0.15-0.17 vs 0.156). Single heldout set, n=150: differences are within noise.
- Teacher size (150M vs 400M) made no consistent difference to the students.

## Recommendation
Candidate limits <=100 MB / <=30 ms: all four qualify (33/33/69/69 MB; p50 9.5/10.8/19.1/23.1 ms).
**Best overall: `t150m_s32m_soup`** (33 MB, ~10 ms): positive difficulty bias, hard pass 0.95, test rho 0.894, cheapest to serve.
If outcome/attempt ranking matters more than latency, `t150m_s68m_seed0` (69 MB, ~19 ms) has the best attempt rho (0.262) and val int8 (87.39).
Not promoted into artifacts/panda-router-v*; v3 stays default until the user picks.

## Modal spend
Total **$1.60** of the $15 cap (16 jobs, estimates = wall time x list price x 1.08). Log: `checkpoints/v4/cost_log.jsonl`.
Note: failed early attempts (container crash loops before training) were not billed to a GPU and are not in the log.
Code: `scripts/modal/train_modal.py`; `--under-w` flag in `scripts/train/train.py`, `panda_router/model/{corn,losses}.py`, `panda_router/train/trainer.py`.
