# Matcher calibration on real attempt-and-grade outcomes (2026-10-26)

The matcher's P(success) is now calibrated against real pass/fail outcomes. The calibration has 3 global
parameters, fitted by maximum likelihood on the train/val attempt cells only. Gold is used only for evaluation.
Calibration fixes the over-confidence: on held-out gold, ECE goes from 0.33 to 0.13 and log-loss from 1.36 to 0.71.
**It does not improve routed success per dollar.** With these cards and this profiler, no `min_p` beats a random mix of
always-cheapest and always-strongest. Two things limit routing:

1. **Card order.** The deepseek card (mean θ 6.09) ranks deepseek below qwen (6.59), but deepseek actually passes more
   often (train .33 vs .21, gold .68 vs .47). Always-deepseek alone scores 67.9 at $0.148 per 100 tasks.
2. **Profiler difficulty.** v2 barely ranks real gold outcomes (see the difficulty-signal table below).

Reproduce: `.venv/bin/python scripts/outcomes/calibrate_matcher.py [--apply] [--profiler onnx:<dir>] [--cards <dir>]`.
It runs on CPU in about 1 minute and makes no API calls. Profiles are cached in `eval_reports/cache/calib_profiles_*.json`
and the full numbers are in `eval_reports/cache/calibration_summary*.json`.

Code: `panda_router/matcher/calibration.py`, wired into `Matcher` in `policy.py`. Shipped parameters:
`panda_router/matcher/calibration.json`. Tests: `tests/test_calibration.py`.

## Method

- **Data.** Fit: 2,204 graded train/val cells (511 tasks × 5 attempters, judge ds-think). Eval: the 140 gold tasks
  that have all 5 cells graded (700 cells). Each task is profiled with `OnnxProfiler('artifacts/panda-router-v2')`, and
  P comes from the current `cards/` and the unchanged `core.py` math.
- **Model.** `P = E_{b,z} sigmoid(a · a_mult · (z + shift_tier − (slope · b + delta)))`. This is the same as core's
  `sigmoid(a'(z' − b))` with `z' = (z + shift − delta)/slope` and `a' = a · a_mult · slope`, so it is applied as a transform of
  (mu, sd, a) just before `core.p_by_level`, in `Matcher._p_by_level`. Routing and `escalate` both use it. `core.py` and the
  training soft matcher are unchanged. `quality = mu/10` stays raw.
- **Switches.** `Matcher(calibration=False)` or `PANDA_ROUTER_CALIBRATION=off` gives raw P. `Matcher(calibration=<path|dict>)`
  loads a different calibration. The JSON is read once (`lru_cache`). Route latency on the full 65-card library is 0.53 ms
  (< 2 ms is tested).
- **Selection.** 5-fold cross-validation grouped by task, scored by log-loss. The rule picks the simplest variant within
  0.005 of the best CV score.

| profiler | none | delta | +slope | +a_mult | +tier shift | chosen |
|---|---:|---:|---:|---:|---:|---|
| v2 | 1.167 | 0.613 | 0.582 | 0.561 | 0.558 | delta+slope+a |
| heuristic | 1.758 | 0.680 | 0.622 | 0.594 | 0.593 | delta+slope+a |
| fixed_average | 0.960 | 0.621 | 0.619 | 0.619 | 0.619 | delta |

**Shipped (v2): delta = 4.37, slope = 0.84, a_mult = 0.44, no tier shifts.** The effective difficulty is
b_eff = 0.84·b + 4.37, so a level-3.5 task (the gold mean) sits at 7.3 on the θ scale, and the effective discrimination is
1.2 × 0.44 = 0.53. The tier variant gains only 0.003 log-loss, and its shifts (small −1.06, mid −2.42) mostly encode
single-card errors: tier:mid is minimax alone here. Applied by tag, those shifts would move every tier:mid card in the
library, so the tier variant is not shipped.

## Diagnosis (train/val cells, v2 profiles)

Reliability, before → after:

| P bin | n | mean P | observed |  | P bin (after) | n | mean P | observed |
|---|---:|---:|---:|---|---|---:|---:|---:|
| 0.0-0.2 | 111 | 0.13 | 0.08 |  | 0.0-0.2 | 651 | 0.13 | 0.11 |
| 0.2-0.4 | 252 | 0.31 | 0.09 |  | 0.2-0.4 | 827 | 0.29 | 0.31 |
| 0.4-0.6 | 323 | 0.50 | 0.13 |  | 0.4-0.6 | 526 | 0.49 | 0.53 |
| 0.6-0.8 | 428 | 0.70 | 0.26 |  | 0.6-0.8 | 197 | 0.68 | 0.59 |
| 0.8-0.9 | 307 | 0.85 | 0.35 |  | 0.8-0.9 | 3 | 0.81 | 0.67 |
| 0.9-1.0 | 783 | 0.97 | 0.55 |  |  | | | |

How much each candidate cause explains:

- **Global offset between the difficulty and θ scales: most of the error.** `delta` alone cuts CV log-loss from 1.17 to
  0.61. Raw mean P is 0.71 against a real pass rate of 0.33.
- **Discrimination a = 1.2 is too high.** a_mult = 0.44 adds a further 0.02 of log-loss. A slope below 1 means the profiler's
  difficulty range is slightly too wide.
- **Card thetas: the per-model order is wrong.** A global transform keeps the card order, so deepseek stays
  under-predicted. On gold, calibrated P is .36 for deepseek and .42 for qwen, while real pass rates are .68 and .47.
  The what-if below shows this is the routing lever.
- **Profiler difficulty: weak signal out of distribution.** The table shows the logistic slope of pass on expected
  difficulty, with a fixed effect per model:

| profiler | train/val: logit per level (E[d] mean ± sd) | gold: logit per level (E[d] mean ± sd) |
|---|---|---|
| v2 | −0.44 (5.35 ± 1.86) | −0.12 (3.50 ± 1.07) |
| heuristic | −0.32 (4.50 ± 1.74) | −0.09 (3.05 ± 0.95) |

v2 was trained on these train rows, so its train slope is in-sample. Fitting on the 47 val tasks only (held out for v2)
gives slope 0.66 and a_mult 0.36, compared with 0.84 and 0.44 on all rows. The full fit therefore slightly over-trusts v2's
difficulty.

Per model (mean P before → after vs observed):

| model | train pass | train P before | train P after | gold pass | gold P before | gold P after |
|---|---:|---:|---:|---:|---:|---:|
| deepseek-v4.1-flash | 0.33 | 0.57 | 0.23 | 0.68 | 0.87 | 0.36 |
| qwen3.8-flash | 0.21 | 0.65 | 0.28 | 0.47 | 0.90 | 0.42 |
| minimax-m3.1-flash | 0.24 | 0.72 | 0.32 | 0.46 | 0.94 | 0.49 |
| gemini-3.8-flash | 0.32 | 0.76 | 0.35 | 0.61 | 0.95 | 0.52 |
| gpt-6.1-sol | 0.55 | 0.88 | 0.48 | 0.79 | 0.98 | 0.64 |

## Probability quality, before → after

| profiler | split | Brier | log-loss | ECE | mean P | pass rate |
|---|---|---|---|---|---|---:|
| v2 | train (2204 cells) | 0.348 → 0.189 | 1.167 → 0.557 | 0.386 → 0.034 | 0.71 → 0.33 | 0.33 |
| **v2** | **gold (700)** | **0.349 → 0.256** | **1.360 → 0.707** | **0.332 → 0.128** | **0.93 → 0.49** | **0.60** |
| heuristic | gold (700) | 0.374 → 0.272 | 1.644 → 0.743 | 0.368 → 0.181 | 0.96 → 0.42 | 0.60 |
| fixed_average | gold (700) | 0.254 → 0.309 | 0.707 → 0.831 | 0.158 → 0.267 | 0.72 → 0.33 | 0.60 |

Gold is much easier than the fit set (0.60 vs 0.33 pass), because the attempt sample over-weights hard, synthetic and
repo-referencing tasks. Calibrated v2 is therefore **under-confident on gold by about 0.1** (0.49 vs 0.60). Here the
profiler does help: v2 sees that gold is easier (E[d] 3.5 vs 5.35 on train/val), so its calibration transfers. The fixed
average profile cannot see this, and its calibration makes gold *worse* (Brier 0.254 → 0.309).

## True routed success on gold (140 tasks; success / 100 and logged $ / 100 tasks)

In the min_p rows, floor = min(min_p, 0.3), so the floor cannot override the threshold. The "old defaults" row uses
min_p 0.75 with floor 0.55.

| policy | v2 uncalibrated | **v2 calibrated** | heuristic cal. | fixed_average cal. |
|---|---|---|---|---|
| old/current defaults (0.75, floor 0.55) | 50.0 / 0.095 | **78.6 / 1.061** | 78.6 / 1.061 | 78.6 / 1.061 |
| min_p=0.3 | 47.1 / 0.064 | 47.9 / 0.115 | 47.9 / 0.128 | 45.7 / 0.114 |
| min_p=0.35 | 47.1 / 0.064 | 52.1 / 0.220 | 52.1 / 0.219 | 60.7 / 0.474 |
| min_p=0.4 | 47.1 / 0.064 | 55.7 / 0.345 | 53.6 / 0.385 | 78.6 / 1.061 |
| min_p=0.45 | 47.1 / 0.064 | 60.7 / 0.563 | 61.4 / 0.693 | 78.6 / 1.061 |
| min_p=0.5 | 47.1 / 0.064 | 60.7 / 0.664 | 70.0 / 0.930 | 78.6 / 1.061 |
| min_p=0.55 | 47.9 / 0.065 | 65.7 / 0.819 | 78.6 / 1.045 | 78.6 / 1.061 |
| min_p=0.6 | 47.9 / 0.068 | 66.4 / 0.941 | 78.6 / 1.061 | 78.6 / 1.061 |
| min_p=0.7 | 49.3 / 0.084 | 78.6 / 1.060 | 78.6 / 1.061 | 78.6 / 1.061 |
| min_p=0.75 | 50.0 / 0.095 | 78.6 / 1.061 | 78.6 / 1.061 | 78.6 / 1.061 |
| min_p=0.8 | 50.0 / 0.147 | 78.6 / 1.061 | 78.6 / 1.061 | 78.6 / 1.061 |
| min_p=0.85 | 50.7 / 0.204 | 78.6 / 1.061 | 78.6 / 1.061 | 78.6 / 1.061 |
| min_p=0.9 | 53.6 / 0.286 | 78.6 / 1.061 | 78.6 / 1.061 | 78.6 / 1.061 |
| max_utility | 45.7 / 0.114 | 45.7 / 0.155 | 45.7 / 0.163 | 45.7 / 0.114 |
| max_quality | 78.6 / 1.061 | 78.6 / 1.061 | 78.6 / 1.061 | 78.6 / 1.061 |

Baselines: always-cheapest (qwen) 47.1 / 0.064 · always-strongest (gpt-6.1-sol) 78.6 / 1.061 ·
always-deepseek 67.9 / 0.148 · always-gemini 60.7 / 0.474 · always-minimax 45.7 / 0.114 · **oracle 90.0 / 0.192**.

The calibrated v2 curve runs from 47.9 at $0.115 to 78.6 at $1.061. It never goes more than +0.1 above the straight line
between always-cheapest and always-strongest (the random-mix line), so this profiler and these cards add no routing skill
beyond a cost/quality dial. The heuristic profiler is about the same. The fixed average profile jumps from one model to
the next as min_p moves.

### What-if: card thetas moved to the train-fit IRT abilities (temporary dir, `cards/` untouched)

Each attempter's 10 axes were shifted so that its mean θ equals the router-scale IRT θ from `REPORT_attempts.md`:
qwen 6.59, minimax 6.95, gemini 7.36, deepseek 7.55, gpt-6.1-sol 8.64. Those thetas come from train/val only, so gold
stays held out. Run with `--cards <dir>`.

| policy (v2, recalibrated on the what-if cards: delta 5.97, slope 0.42) | success / $ |
|---|---|
| min_p=0.4 | 58.6 / 0.304 |
| min_p=0.55 | 74.3 / 0.749 (+5.6 above the mix line) |
| max_utility | **68.6 / 0.185** (+17.7; deepseek 137/140) |

Fixing the card order, and above all deepseek's θ, is what moves routing toward the oracle. This repo does not apply it
(see the caveats).

## Defaults decision

**Kept `min_p_success` = 0.75 and `floor` = 0.55** (`DEFAULTS` in `policy.py` unchanged). Reasons:

- On **train** routing (the 330 train/val tasks with all 5 cells graded, used so that gold never chooses a default), every
  calibrated min_p falls on or below the cheapest↔strongest line: gains range from −1.6 to +0.0. No setting is clearly
  better on success per dollar.
- On gold the best gain is +0.1 (min_p 0.35), well inside noise (SE about 4 points at n = 140).
- With calibration, 0.75 now means what it says: route to a model with a real ≥ 75% chance. On gold only gpt-6.1-sol
  clears that (78.6% observed), so routing nearly every task there is the correct reading of the threshold.

**Behaviour change.** With the same defaults, routing on this 5-model pool moves from 50.0 / $0.095 to 78.6 / $1.061, about
11× the cost. Cost-sensitive callers should pass `min_p_success` 0.35–0.45 with `floor` ≤ min_p, which gives 52–61 at
$0.22–0.56 on gold. `PANDA_ROUTER_CALIBRATION=off` restores the old behaviour.

## Caveats

- Non-SWE, single-turn, no-tools tasks only. Many synthetic tasks reference repositories the model cannot see, which
  drags train/val pass rates down. That is the main reason for the train/gold shift.
- Labels come from one LLM judge (deepseek-v4.1-flash, κ 0.85 vs kimi-k3.1-pro, not human-validated). Deepseek is both
  an attempter and the judge. The bulk self-preference check is still blocked by credits.
- Only 140 gold tasks and 5 attempters. Calibration is fitted for **this profiler and these cards**. Refit with
  `--profiler onnx:artifacts/panda-router-v3 --apply` when v3 ships, or when cards change.
- v2 was trained on the train rows, so its difficulty is in-sample there (see the val-only fit above).
- The tier variant is fitted and reported but not shipped, because it would move whole tiers of library cards based on
  one or two models.
