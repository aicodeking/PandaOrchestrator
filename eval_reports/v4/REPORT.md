# Panda Router v4.1: calibrated success head, anchor + escalation-ladder policy, vague-task profiler (2026-10-27)

v4.1 replaces the first v4 ship (v4.0) after the architect review: v4.0's P was deflated (fail-weight 2.5 + lower bound
shown as the estimate: mean 0.25 vs 0.62 real on gold), min_p 0.5 was never met, and single-shot (74.0 @ $0.96) was
below always-gpt-6.1-sol (79.3 @ $1.11). Gold (150 held-out tasks graded for all 9 attempters) was never used for
fitting or tuning; it was evaluated once for v4.1 (and re-run once after a bug fix for cards outside the gold pools,
which changed no gold row).

## Verdict

- **85/100 single-shot: not reached, and not reachable with this data.** v4.1 single-shot (max_utility, default) is
  **76.7 [69.3, 82.7] at $0.91/100**, vs always-gpt-6.1-sol 79.3 [72.7, 85.3] at $1.11: within the CI at lower cost (the
  review's floor). The head ranks tasks well (CV AUC 0.745) but cannot tell strong models apart per task, so the
  policy anchors on the best-evidence model and only moves to cheaper ones when they are as likely to pass.
- **85 within 2 attempts: reached.** Following `escalation_ladder`: **88.7 [83.3, 93.3] within 2 attempts at
  $0.88/100** (target >= 85 at < $1.20), 92.0 [87.3, 96.0] within 3 at $1.23, vs v3's cascade 86.7 @ $0.58 (2) /
  92.0 @ $0.94 (3), and always-strongest (opus) 76.7 @ $4.03. Failure signal in the simulation = the judge label.
  4-subscription pool: 84.7 within 2 at $1.24 (just misses), 90.7 within 3 at $2.01.
- **P is now calibrated on train/val** (nested-CV ECE 0.015, mean 0.352 vs 0.352 pass rate); the decision uses an
  explicit bound (mean margin 0.039). On gold it still under-states (mean 0.50 vs 0.62, ECE 0.127, was 0.375):
  gold tasks are easier at equal predicted difficulty (see Known limitation).
- **$0 picks:** v3 "cheapest that passes" picked a $0 card for 88% of gold texts on the full default pool; v4.1: 0%
  in all modes. 'HTTP 418' -> deepseek-v4.1-flash ($0.0002); 'a model trainer' -> paid model, difficulty 5.3;
  lock-free MPMC -> gpt-6.1-sol (coding theta 9.25).
- **Under-estimation** (first pick failed while a stronger pool model passed), 9-model gold: v3 max_utility 0.267,
  v4.0 0.173, **v4.1 0.140**; over-spend 0.580 / 0.680 / 0.687.

## Before / after (gold)

| gold metric | v4.0 (first ship) | v4.1 (calibrated) |
|---|---|---|
| 9-model: ECE of displayed p_success (mean P vs pass rate) | 0.375 (0.25 vs 0.62) | 0.127 (0.50 vs 0.62) |
| 9-model: AUC of displayed P | 0.617 | 0.650 |
| 4 subscription: ECE of displayed p_success (mean P vs pass rate) | 0.435 (0.23 vs 0.66) | 0.154 (0.51 vs 0.66) |
| 4 subscription: AUC of displayed P | 0.578 | 0.613 |
| 9-model: single-shot max_utility | 74.0 [66.7, 80.7] @ $0.96; under 0.173, over 0.680 | 76.7 [69.3, 82.7] @ $0.91; under 0.140, over 0.687 |
| 9-model: single-shot cheapest_above_threshold | 74.7 [67.3, 81.3] @ $0.96; under 0.167, over 0.687 | 76.0 [68.7, 82.0] @ $0.88; under 0.147, over 0.680 |
| 9-model: cascade <= 2 attempts | 87.3 [82.0, 92.7] @ $1.50; under 0.173, over 0.680 | 88.7 [83.3, 93.3] @ $0.88; under 0.167, over 0.660 |
| 9-model: cascade <= 3 attempts | 91.3 [86.7, 96.0] @ $1.76; under 0.173, over 0.680 | 92.0 [87.3, 96.0] @ $1.23; under 0.167, over 0.660 |
| 4 subscription: single-shot max_utility | 72.7 [65.3, 80.0] @ $2.01; under 0.107, over 0.560 | 72.7 [65.3, 79.3] @ $1.93; under 0.127, over 0.593 |
| 4 subscription: single-shot cheapest_above_threshold | 73.3 [66.0, 80.7] @ $2.24; under 0.093, over 0.567 | 72.7 [65.3, 79.3] @ $1.93; under 0.127, over 0.593 |
| 4 subscription: cascade <= 2 attempts | 83.3 [77.3, 89.3] @ $2.49; under 0.107, over 0.560 | 84.7 [78.7, 90.0] @ $1.24; under 0.240, over 0.427 |
| 4 subscription: cascade <= 3 attempts | 89.3 [84.0, 94.0] @ $2.84; under 0.107, over 0.560 | 90.7 [85.3, 94.7] @ $2.01; under 0.240, over 0.427 |
| $0 pick rate, full default pool, cheapest mode (v3: 0.88) | 0.00 | 0.00 |

## Review probes (full 65-card default pool)

| request | mode | pick | p_success (lower) | est $ | difficulty (raw) | escalation_ladder |
|---|---|---|---|---|---|---|
| What does HTTP status 418 mean? | cheapest_above_threshold | openrouter-deepseek-v4.1-flash | 0.55 (0.47) | 0.0002 | 2.13 (2.13) | openrouter-deepseek-v4.1-flash 0.55 -> openrouter-gpt-6.1-sol 0.59 -> claude-opus-5.5 0.49 |
| What does HTTP status 418 mean? | max_utility | openrouter-deepseek-v4.1-flash | 0.55 (0.47) | 0.0002 | 2.13 (2.13) | openrouter-deepseek-v4.1-flash 0.55 -> openrouter-gpt-6.1-sol 0.59 -> claude-opus-5.5 0.49 |
| What does HTTP status 418 mean? | max_quality | openrouter-deepseek-v4.1-flash | 0.55 (0.47) | 0.0002 | 2.13 (2.13) | openrouter-deepseek-v4.1-flash 0.55 -> openrouter-gpt-6.1-sol 0.59 -> claude-opus-5.5 0.49 |
| a model trainer | cheapest_above_threshold | claude-haiku-5.5 | 0.59 (0.44) | 0.0007 | 5.26 (4.09) | openrouter-gemini-3.8-flash 0.68 -> claude-sonnet-5.5 0.76 -> openrouter-gpt-6.1-sol 0.64 |
| a model trainer | max_utility | openrouter-gemini-3.8-flash | 0.68 (0.48) | 0.0061 | 5.26 (4.09) | openrouter-gemini-3.8-flash 0.68 -> claude-sonnet-5.5 0.76 -> openrouter-gpt-6.1-sol 0.64 |
| a model trainer | max_quality | openrouter-gemini-3.8-flash | 0.68 (0.48) | 0.0061 | 5.26 (4.09) | openrouter-gemini-3.8-flash 0.68 -> claude-sonnet-5.5 0.76 -> openrouter-gpt-6.1-sol 0.64 |
| Implement a lock-free MPMC queue in Rust | cheapest_above_threshold | openrouter-gpt-6.1-sol | 0.62 (0.57) | 0.0381 | 8.20 (8.20) | openrouter-gpt-6.1-sol 0.62 -> openrouter-kimi-k3.1-pro 0.49 -> claude-fable-5.1 0.50 |
| Implement a lock-free MPMC queue in Rust | max_utility | openrouter-gpt-6.1-sol | 0.62 (0.57) | 0.0381 | 8.20 (8.20) | openrouter-gpt-6.1-sol 0.62 -> openrouter-kimi-k3.1-pro 0.49 -> claude-fable-5.1 0.50 |
| Implement a lock-free MPMC queue in Rust | max_quality | openrouter-gpt-6.1-sol | 0.62 (0.57) | 0.0381 | 8.20 (8.20) | openrouter-gpt-6.1-sol 0.62 -> openrouter-kimi-k3.1-pro 0.49 -> claude-fable-5.1 0.50 |

p_success is documented in every response (`router.p_success_note`): "estimated pass rate under strict grading
(success head calibrated on train/val outcomes; card prior for cards it was not trained on); decisions use
p_success_lower". Gemini-3.8-flash / deepseek / sol are within the 0.05 equal-P margin on these prompts, so the
cheaper one is picked.

## Known limitation: P for trivial tasks is understated

The outcome data has very few trivial, well-specified questions: train/val cells the profiler rates <= 2 pass only
0.44-0.53 (many look easy but lack context or are obscure), and stacking the card IRT P adds nothing in CV
(coefficient 0.04). So the calibrated P for 'What does HTTP 418 mean?' is ~0.55 for every model, and on gold
(easier at equal predicted difficulty: 0.64-0.78 at difficulty <= 2) P is under-stated by ~0.12 on average. The
policy copes by treating roughly equal P as a tie that goes to the cheaper card. Fix: collect graded outcomes for
~100 trivial factual / small-edit questions across the 9 attempters (the v4 attempt-and-grade harness) and refit the
head; until then, treat absolute P on trivial tasks as a strict lower estimate.

## 1. Profiler (requirement D)

Base: `t150m_s32m_soup` (eval_reports/v4_profiler). Fine-tuned on Modal (L40S, 110 s, **$0.065**) on
data/train.jsonl + data/vague_v4/train.jsonl, validated on data/val + vague_v4/val (`scripts/modal/success_modal.py`,
warm start from the soup, same anchors / `--under-w 2.5` recipe, no distillation, 3 epochs, lr 3e-5, best = epoch 3,
val 86.97). The full fine-tune over-shot easy prompts (HTTP 418 -> 2.24), so the shipped weights are a WiSE
interpolation 0.7 x fine-tuned + 0.3 x soup (local, no GPU), exported int8 per-channel (31 MB).

| probe (expected difficulty, int8) | v3 | soup | fine-tuned | **shipped (WiSE 0.7)** | target |
|---|---|---|---|---|---|
| a model trainer | 1.47 | 2.02 | 5.30 | **4.09** | >= 4 |
| train a model | 1.54 | 2.21 | 5.17 | **4.36** | >= 4 |
| What does HTTP 418 mean? | 1.55 | 1.70 | 2.24 | **1.97** | <= 2 |

The router additionally widens underspecified inputs toward the population prior (vagueness = excess ambiguity
(ambiguous_spec above 0.5, rescaled) x shortness, mix weight 0.7 x vagueness, never lowering the mean): 'a model
trainer' decides on 5.26; HTTP 418 (ambiguity 0.16) is not widened.
Margins on the probes are small (0.09 / 0.03); they are pinned in tests/test_router_v4.py.

Gold/test profiler metrics (not worse than the soup beyond noise):

| profiler | gold cat acc | gold diff rho | gold diff MAE | gold diff bias | test cat acc | test diff rho | test bias | attempt-IRT rho |
|---|---|---|---|---|---|---|---|---|
| v3 | 0.652 | 0.549 | 1.032 | +0.16 | 0.748 | 0.845 | -0.08 | 0.212 |
| t150m_s32m_soup | 0.682 | 0.721 | 0.856 | +0.12 | 0.786 | 0.894 | +0.02 | 0.137 |
| soup+vague ft (1.0) | 0.685 | 0.710 | 0.873 | +0.13 | 0.793 | 0.884 | -0.00 | 0.134 |
| soup+vague ft, WiSE 0.7 | 0.696 | 0.718 | 0.861 | +0.12 | 0.803 | 0.888 | +0.00 | 0.144 |

(v3 row = `eval_reports/v3/a10_*`, the v3 artifact's eval files.)

## 2. Success head P(pass | task, model)
## 2. Success head P(pass | task, model), v4.1

`scripts/outcomes/train_success_head.py` -> `artifacts/panda-router-v4/success_head.json`. Frozen v4-profiler
features (78 dims), joint logistic over the 9 attempter cards (shared + per-card weights), **unweighted** (v4.0 used
fail-weight 2.5), 16 task-bootstraps; then **per-card Platt calibration** of the bootstrap-mean logit, fitted on
out-of-fold predictions (nested 5-fold for the reported numbers). Displayed `p_success` = Platt(mean logit);
`p_success_lower` = Platt(mean - 1.0 x bootstrap sd), the explicit over-estimation margin (mean 0.039). Trained on
5,709 train/val cells (879 tasks); gold excluded.

| train/val (out-of-fold) | ECE | log-loss | AUC | mean P (pass rate 0.352) |
|---|---|---|---|---|
| v4.0 head (fail-weight 2.5) | - | 0.636 | 0.735 | 0.204 |
| v4.1 head, raw | 0.019 | 0.573 | 0.734 | 0.351 |
| **v4.1 head + per-card Platt (nested CV)** | **0.015** | **0.560** | **0.745** | **0.352** |

Reliability (v4.1, nested CV):

| P bin | cells | mean P | pass rate |
|---|---|---|---|
| 0.0-0.1 | 661 | 0.063 | 0.056 |
| 0.1-0.2 | 942 | 0.150 | 0.144 |
| 0.2-0.3 | 914 | 0.251 | 0.266 |
| 0.3-0.4 | 859 | 0.349 | 0.376 |
| 0.4-0.5 | 813 | 0.451 | 0.437 |
| 0.5-0.6 | 754 | 0.549 | 0.554 |
| 0.6-0.7 | 539 | 0.643 | 0.638 |
| 0.7-0.8 | 195 | 0.742 | 0.656 |
| 0.8-0.9 | 32 | 0.833 | 0.781 |

Per-card CV AUC: qwen 0.76, gemini 0.78, deepseek 0.73, minimax 0.69, sonnet 0.67, sol 0.65, haiku 0.62, luna 0.60,
opus 0.57 (150 tasks). Population base rates (mean calibrated P over all 879 train/val tasks, comparable across cards):
sol 0.61, sonnet 0.55, opus 0.48, haiku 0.45, deepseek 0.35, gemini 0.30, luna 0.28, minimax 0.21, qwen 0.17.
End-to-end success model on Modal: not run (the frozen head is calibrated and the bottleneck is 879 labelled tasks).

Cards the head was not trained on: card IRT P at the 75th-percentile difficulty, interpolated per task against the
covered cards' (card P -> head P) pairs (clamped: an unproven card never exceeds the best evidence-backed one), minus a
prior penalty (benchmark-informed 0.5, estimated 1.0, +0.5 for $0/local logits); after a failure they get the mean
correlated-failure shift (-0.70 logits) instead of being treated as independent.

## 3. Policy v4.1 and tuning (train/val only)

`panda_router/router_v4/policy.py` (`choose`, `ladder`), used by `Matcher(policy="v4")` (default):
- **Anchor** = the candidate with the highest population base rate (best-evidence card; uncovered cards cannot anchor
  when a covered card is in the pool). Decisions use p_success_lower.
- Cheaper cards compete only if clearly safe (lower bound >= min_p) or **roughly equal** (calibrated P within 0.05 of
  the anchor's). Then cheapest_above_threshold = min expected cost E_m = c_m + (1-P_m)(c_next + L); max_utility =
  max P - w_cost E/maxE; max_quality = max P. Final step in every mode: a meaningfully cheaper card with calibrated P
  within 0.05 replaces the pick (architect rule: never the pricier card at equal P). Exact cost ties -> stronger card.
  $0 cards only within 0.05 of the best paid card.
- **`escalation_ladder`** (response field): ordered pair (a, b) maximising S2 - lambda C2 with
  S2 = P_a + (1-P_a) P(b | a failed) (head failure-correlation offsets), C2 = c_a + (1-P_a) c_b, then the most likely
  remaining card; `/escalate` follows the previous response's ladder (`decided_by: escalation_ladder`).

Pre-registered selection (8-model train/val pool, 399 tasks, out-of-fold calibrated bounds, eval_reports/v4/tune.json):
single-shot = max success with $ <= the best single model's $ (always-sol $1.52), ties -> lower under-estimation ->
lower $; ladder = max success within 2 attempts with $ <= the same cap. Equal-P margin fixed at 0.05 by the review
requirement (~ the head's uncertainty; disabling it scores ~1 point higher on train/val, within noise).
Selected: **min_p 0.6, L $0.10, w_cost 1.0, equal-P margin 0.05, ladder lambda 3.0** (`V4_DEFAULTS`).
Train/val at these settings: single-shot 55.1 @ $1.37-1.38 (8-model; always-sol 56.4 @ $1.52), 53.7 @ $1.38
(9-model; sol 57.0 @ $1.54); ladder within 2: 64.9 @ $1.48 (8-model), 65.1 @ $1.63 (9-model).

## 4. Gold results (bootstrap 95% CIs over tasks, 1000 resamples)

$ = logged OpenRouter attempt cost; subscription models priced as in data/outcomes/REPORT_v4_attempts.md (chars/4 input +
logged output tokens x card price). under-est = first pick failed while a stronger (card skills) pool model passed;
over-spend = first pick passed while a cheaper model also passed. v3 = v3 profiler + v3 policy (calibration off).
"v4 max_utility cascade" = route then `/escalate` (which follows the ladder after the first failure); "escalation_ladder
within k" = start at the ladder's first rung. Cascade $ includes every failed attempt.

**9-model pool** (150 gold tasks graded for every model; cheap = card price <= $1/Mtok in+out: claude-haiku-5.5, codex-gpt-6-luna, openrouter-minimax-m3.1-flash, openrouter-qwen3.8-flash)

| strategy | success /100 [95% CI] | $ /100 [95% CI] | under-est | over-spend | cheap picks (fail) | attempts |
|---|---|---|---|---|---|---|
| always-cheapest (card price) | 64.0 [56.0, 70.7] | 0.121 [0.103, 0.142] | 0.293 | 0.560 | 1.00 (0.36) | 1.00 |
| always-strongest (card skills) | 76.7 [70.0, 83.3] | 4.030 [3.578, 4.472] | 0.000 | 0.760 | 0.00 (-) | 1.00 |
| oracle (cheapest passing) | 94.0 [90.0, 97.3] | 0.560 [0.322, 0.839] | 0.000 | 0.000 | 0.73 (0.00) | 1.00 |
| always claude-haiku-5.5 | 64.0 [56.0, 70.7] | 0.121 [0.103, 0.142] | 0.293 | 0.560 | 1.00 (0.36) | 1.00 |
| always claude-opus-5.5 | 76.7 [70.0, 83.3] | 4.030 [3.578, 4.472] | 0.000 | 0.760 | 0.00 (-) | 1.00 |
| always claude-sonnet-5.5 | 73.3 [66.0, 80.0] | 2.040 [1.812, 2.279] | 0.193 | 0.720 | 0.00 (-) | 1.00 |
| always codex-gpt-6-luna | 51.3 [43.3, 59.3] | 0.035 [0.029, 0.041] | 0.420 | 0.007 | 1.00 (0.49) | 1.00 |
| always openrouter-deepseek-v4.1-flash | 65.3 [57.3, 72.7] | 0.152 [0.135, 0.172] | 0.280 | 0.520 | 0.00 (-) | 1.00 |
| always openrouter-gemini-3.8-flash | 60.7 [52.6, 68.7] | 0.492 [0.447, 0.538] | 0.327 | 0.593 | 0.00 (-) | 1.00 |
| always openrouter-gpt-6.1-sol | 79.3 [72.7, 85.3] | 1.114 [0.986, 1.246] | 0.107 | 0.747 | 0.00 (-) | 1.00 |
| always openrouter-minimax-m3.1-flash | 45.3 [37.3, 53.3] | 0.120 [0.106, 0.133] | 0.487 | 0.373 | 1.00 (0.55) | 1.00 |
| always openrouter-qwen3.8-flash | 45.3 [36.7, 53.3] | 0.068 [0.060, 0.075] | 0.487 | 0.393 | 1.00 (0.55) | 1.00 |
| v3 cheapest_above_threshold single-shot | 65.3 [57.3, 72.0] | 0.202 [0.132, 0.290] | 0.280 | 0.533 | 0.95 (0.36) | 1.00 |
| v3 cheapest_above_threshold cascade<= 2 attempts | 80.0 [73.3, 86.0] | 0.492 [0.346, 0.649] | 0.280 | 0.533 | 0.95 (0.36) | 1.35 |
| v3 cheapest_above_threshold cascade<= 3 attempts | 90.0 [84.7, 94.7] | 1.056 [0.745, 1.470] | 0.280 | 0.533 | 0.95 (0.36) | 1.55 |
| v3 max_utility single-shot | 66.7 [59.3, 73.3] | 0.234 [0.160, 0.327] | 0.267 | 0.580 | 0.89 (0.35) | 1.00 |
| v3 max_utility cascade<= 2 attempts | 86.7 [81.3, 92.0] | 0.580 [0.433, 0.753] | 0.267 | 0.580 | 0.89 (0.35) | 1.33 |
| v3 max_utility cascade<= 3 attempts | 92.0 [87.3, 96.0] | 0.944 [0.669, 1.264] | 0.267 | 0.580 | 0.89 (0.35) | 1.47 |
| v3 max_quality single-shot | 76.7 [70.0, 83.3] | 4.030 [3.578, 4.472] | 0.000 | 0.760 | 0.00 (-) | 1.00 |
| v3 max_quality cascade<= 2 attempts | 90.0 [85.3, 94.7] | 4.346 [3.830, 4.864] | 0.000 | 0.760 | 0.00 (-) | 1.23 |
| v3 max_quality cascade<= 3 attempts | 92.7 [88.0, 96.7] | 4.652 [4.104, 5.262] | 0.000 | 0.760 | 0.00 (-) | 1.33 |
| v4 cheapest_above_threshold single-shot | 76.0 [68.7, 82.0] | 0.884 [0.758, 1.027] | 0.147 | 0.680 | 0.01 (0.50) | 1.00 |
| **v4 max_utility single-shot** | 76.7 [69.3, 82.7] | 0.909 [0.777, 1.052] | 0.140 | 0.687 | 0.01 (0.50) | 1.00 |
| v4 max_utility cascade<= 2 attempts | 89.3 [84.0, 94.0] | 1.118 [0.951, 1.304] | 0.140 | 0.687 | 0.01 (0.50) | 1.23 |
| v4 max_utility cascade<= 3 attempts | 91.3 [86.7, 95.3] | 1.304 [1.086, 1.561] | 0.140 | 0.687 | 0.01 (0.50) | 1.34 |
| v4 max_quality single-shot | 76.7 [69.3, 82.7] | 0.911 [0.778, 1.052] | 0.140 | 0.687 | 0.01 (1.00) | 1.00 |
| v4 escalation_ladder within 1 | 76.0 [68.7, 82.7] | 0.564 [0.431, 0.700] | 0.167 | 0.660 | 0.09 (0.23) | 1.00 |
| **v4 escalation_ladder within 2** | 88.7 [83.3, 93.3] | 0.884 [0.700, 1.080] | 0.167 | 0.660 | 0.09 (0.23) | 1.24 |
| **v4 escalation_ladder within 3** | 92.0 [87.3, 96.0] | 1.234 [0.924, 1.593] | 0.167 | 0.660 | 0.09 (0.23) | 1.35 |

**4 subscription pool** (150 gold tasks graded for every model; cheap = card price <= $1/Mtok in+out: claude-haiku-5.5, codex-gpt-6-luna)

| strategy | success /100 [95% CI] | $ /100 [95% CI] | under-est | over-spend | cheap picks (fail) | attempts |
|---|---|---|---|---|---|---|
| always-cheapest (card price) | 64.0 [56.0, 70.7] | 0.121 [0.103, 0.142] | 0.260 | 0.407 | 1.00 (0.36) | 1.00 |
| always-strongest (card skills) | 76.7 [70.0, 83.3] | 4.030 [3.578, 4.472] | 0.000 | 0.720 | 0.00 (-) | 1.00 |
| oracle (cheapest passing) | 91.3 [86.7, 96.0] | 1.087 [0.753, 1.478] | 0.000 | 0.000 | 0.75 (0.00) | 1.00 |
| always claude-haiku-5.5 | 64.0 [56.0, 70.7] | 0.121 [0.103, 0.142] | 0.260 | 0.407 | 1.00 (0.36) | 1.00 |
| always claude-sonnet-5.5 | 73.3 [66.0, 80.0] | 2.040 [1.812, 2.279] | 0.120 | 0.613 | 0.00 (-) | 1.00 |
| always claude-opus-5.5 | 76.7 [70.0, 83.3] | 4.030 [3.578, 4.472] | 0.000 | 0.720 | 0.00 (-) | 1.00 |
| always codex-gpt-6-luna | 51.3 [43.3, 59.3] | 0.035 [0.029, 0.041] | 0.400 | 0.000 | 1.00 (0.49) | 1.00 |
| v3 cheapest_above_threshold single-shot | 63.3 [55.3, 70.0] | 0.249 [0.142, 0.391] | 0.253 | 0.367 | 0.97 (0.36) | 1.00 |
| v3 cheapest_above_threshold cascade<= 2 attempts | 80.0 [73.3, 86.0] | 0.989 [0.643, 1.385] | 0.253 | 0.367 | 0.97 (0.36) | 1.37 |
| v3 cheapest_above_threshold cascade<= 3 attempts | 87.3 [81.3, 92.0] | 1.704 [1.197, 2.302] | 0.253 | 0.367 | 0.97 (0.36) | 1.57 |
| v3 max_utility single-shot | 64.0 [56.0, 70.7] | 0.133 [0.107, 0.164] | 0.260 | 0.407 | 0.99 (0.36) | 1.00 |
| v3 max_utility cascade<= 2 attempts | 83.3 [76.7, 89.3] | 1.006 [0.779, 1.258] | 0.260 | 0.407 | 0.99 (0.36) | 1.36 |
| v3 max_utility cascade<= 3 attempts | 90.0 [84.7, 94.0] | 1.874 [1.361, 2.463] | 0.260 | 0.407 | 0.99 (0.36) | 1.53 |
| v3 max_quality single-shot | 76.7 [70.0, 83.3] | 4.030 [3.578, 4.472] | 0.000 | 0.720 | 0.00 (-) | 1.00 |
| v3 max_quality cascade<= 2 attempts | 85.3 [79.3, 90.7] | 4.615 [4.070, 5.199] | 0.000 | 0.720 | 0.00 (-) | 1.23 |
| v3 max_quality cascade<= 3 attempts | 90.0 [84.7, 94.0] | 4.643 [4.092, 5.236] | 0.000 | 0.720 | 0.00 (-) | 1.38 |
| v4 cheapest_above_threshold single-shot | 72.7 [65.3, 79.3] | 1.935 [1.707, 2.169] | 0.127 | 0.593 | 0.06 (0.33) | 1.00 |
| **v4 max_utility single-shot** | 72.7 [65.3, 79.3] | 1.935 [1.707, 2.169] | 0.127 | 0.593 | 0.06 (0.33) | 1.00 |
| v4 max_utility cascade<= 2 attempts | 84.7 [78.7, 90.0] | 2.090 [1.839, 2.346] | 0.127 | 0.593 | 0.06 (0.33) | 1.27 |
| v4 max_utility cascade<= 3 attempts | 88.0 [82.0, 92.7] | 2.210 [1.935, 2.521] | 0.127 | 0.593 | 0.06 (0.33) | 1.43 |
| v4 max_quality single-shot | 72.7 [65.3, 79.3] | 1.935 [1.707, 2.169] | 0.127 | 0.593 | 0.06 (0.33) | 1.00 |
| v4 escalation_ladder within 1 | 63.3 [56.0, 70.7] | 0.465 [0.314, 0.624] | 0.240 | 0.427 | 0.77 (0.40) | 1.00 |
| **v4 escalation_ladder within 2** | 84.7 [78.7, 90.0] | 1.238 [0.989, 1.519] | 0.240 | 0.427 | 0.77 (0.40) | 1.37 |
| **v4 escalation_ladder within 3** | 90.7 [85.3, 94.7] | 2.013 [1.538, 2.581] | 0.240 | 0.427 | 0.77 (0.40) | 1.52 |

**$0 pick rate on the full default card pool (67 cards, gold task texts, no outcomes for local cards)**

| router mode | v3 | v4 |
|---|---|---|
| cheapest_above_threshold | 0.88 | 0.00 |
| max_utility | 0.00 | 0.00 |
| max_quality | 0.00 | 0.00 |

## 5. Latency, artifacts, Modal

- Route latency (int8 profiler + head + policy + ladder, 65-card default pool, CPU, batch 1): tests assert median <= 30 ms
  on short prompts (observed ~4-6 ms after warm-up; long 512-token inputs are dominated by the profiler).
- `artifacts/panda-router-v4/`: model.int8.onnx (committed), model.onnx (fp32, git-ignored), tokenizer, heads.json,
  metrics.json (profiler val + `v4_router` summary), success_head.json (v4.1: unweighted, `platt`, `base_rate`,
  `calibration`, `escalation_logit`). Serve, CLI, MCP and pandacode-run.sh default to it;
  `PANDA_ROUTER_SUCCESS_HEAD=off` / `Matcher(policy="v3", success_head=None)` restore v3 behaviour.
- Modal: this work **$0.065** (1 job, profiler fine-tune); project total **$1.67** of $30 (checkpoints/v4/cost_log.jsonl).
  The v4.1 changes needed no GPU.

## 6. Caveats

- n = 150 gold tasks: CIs are +-6-8 points. v4.1 vs always-sol single-shot (-2.6) and the cascade differences vs v3 are
  within noise; v4.1's ladder is ~$0.30/100 dearer than v3's cascade at 2 attempts for +2 points.
- Cascades assume a reliable failure signal (here the judge label); in PandaCode: tests, a verifier or the user.
- Cards of the 9 attempters were updated by an IRT fit that included gold cells (favours the card-based v3 on gold);
  the head never saw gold.
- The failure-correlation table and the card-prior mapping are fitted on all of train/val and used in-sample in tuning.
- The head's base rates make gpt-6.1-sol the anchor in any pool containing it; picks vary by task mainly through the
  cheap-and-safe / equal-P rules (easy tasks -> deepseek/haiku/gemini) and the ladder.

Reproduce: `.venv/bin/python scripts/outcomes/train_success_head.py --profiler artifacts/panda-router-v4 --out
artifacts/panda-router-v4/success_head.json --C 0.01`; `.venv/bin/python scripts/eval/v4_eval.py tune --out
eval_reports/v4/tune.json`; `.venv/bin/python scripts/eval/v4_eval.py gold --out eval_reports/v4/gold.json
[--old-head <v4.0 head>]`. v4.0 gold results: eval_reports/v4/gold_v40.json.
