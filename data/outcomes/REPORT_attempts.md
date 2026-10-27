# Attempt-and-grade outcomes for non-SWE tasks (2026-10-26)

Real models answered real router tasks and a validated judge graded the answers. A 1PL IRT fit on tasks × models
then gives outcome-grounded difficulties and model abilities on the router 0..10 scale. These complement the
SWE-bench fit in `REPORT.md`, which covers agentic coding only.

Reproduce (resumable, every call cached in `raw/attempts/`, which is git-ignored):
`scripts/outcomes/attempts.py select|subset|attempt|rubric|judge --judge ds-think|validate --judge {ds-think,ds-strict,strong,kimi}`,
then `scripts/outcomes/build_attempts.py [--apply]`. Code: `panda_router/outcomes/grade.py` (client, prompts, sandboxed
run check, kappa) and `irt.py` (`fit_b_given_theta`, `fit_theta_given_b`). Tests: `tests/test_outcomes.py`.
The OpenRouter key is read from opencode's `auth.json` into memory at call time. It is never logged or written.

## What was run

| Step | Detail |
|---|---|
| Tasks | 1,500 sampled from `data/{train,val}.jsonl`, stratified by top category × teacher-difficulty band (1–3.5, 3.5–5.5, 5.5–7.5, 7.5–10) with sqrt allocation. Self-contained tasks (`requires_tools: false`) are taken first within a stratum. swe-rebench/swe-smith rows and anything matching gold by id or text are excluded. The budget then cut this to a **999-task subset** with the same strata proportions (`raw/attempts/subset.json`). Hard groups (hard/scary/deceptive) are included. Plus **150 gold** non-SWE rows (WildChat), used **for evaluation only**. |
| Attempters | `deepseek/deepseek-v4.1-flash`, `qwen/qwen3.8-flash`, `minimax/minimax-m3.1-flash`, `google/gemini-3.8-flash`, `openai/gpt-6.1-sol`. gpt-6.1-sol was picked over kimi-k3.1-pro because it cost $0.012/task vs $0.031/task in a 6-task pilot. Each model gets one turn with no tools. The system prompt says there is no repository access and asks for ≤ ~1,000 words. `max_tokens` is 5,000 and the reasoning budget is `max_tokens: 1500` for every model (qwen ignores `effort: low` and spent all 4k tokens thinking). DeepSeek and MiniMax often ignore the reasoning cap: 37% and 33% of their train/val answers hit the length limit, and a truncated answer is graded as truncated. Ollama gpt-oss:20b is **not installed**, so it was skipped (no pulls). |
| Rubric | One blind checklist per task (3–6 criteria, 1–3 critical), written by deepseek-v4.1-flash without thinking. All five answers share it. |
| Judge | deepseek-v4.1-flash, `reasoning effort: low`. It grades pass/fail against the checklist and never sees which model answered. **Programmatic check:** if an answer to a non-chat, non-docs task has exactly one stdlib-only Python block, that block runs under `python -I` in a temp dir with a 10 s timeout, and a crash or timeout fails the answer: 39 cells (10 ran, 29 failed). The tasks carry no ground-truth answers or tests, so math is checked only by the judge recomputing it. |

## Judge validation (100 gold answers, fixed random sample)

The spec's κ ≥ 0.6 rule was checked against both strong judges. gpt-6.1-sol is also an attempter, so it grades its own
answers. kimi-k3.1-pro is not an attempter, so it was added as the neutral reference.

| Judge | vs kimi-k3.1-pro κ (95% CI) | vs gpt-6.1-sol κ (95% CI) | Pass rate (kimi 0.60, sol 0.43) | $/item |
|---|---|---|---|---|
| ds (deepseek, no thinking) | 0.46 (0.28–0.63) | 0.24 (0.11–0.38) | 0.78 | 0.0002 |
| ds-strict (no thinking, evidence per criterion, verdict computed in code) | 0.39 (0.25–0.53) | 0.34 (0.15–0.51) | 0.28 | 0.0007 |
| **ds-think (deepseek, effort low): label judge** | **0.85 (0.73–0.95)** | 0.53 (0.37–0.68) | 0.62 | 0.0022 |
| gpt-6.1-sol | 0.63 (0.49–0.76) | n/a | 0.43 | 0.0053 |

Passes per answering model (n, ds-think / kimi / gpt-6.1-sol): deepseek 18: 11/11/3, qwen 19: 8/8/4, minimax 17: 8/7/6,
gemini 17: 10/9/7, gpt-6.1-sol 29: 24/25/23. gpt-6.1-sol as judge is much harsher on other models' answers (0.28 vs
kimi 0.49) than on its own (0.79 vs 0.86). The deepseek judge does not favour deepseek's answers relative to kimi (11 vs 11).
**Decision:** ds-think labels every cell (κ 0.85 vs the neutral judge), and gpt-6.1-sol labels are kept as a sensitivity
fit. ds-think's own reasoning loops exhaust 8k tokens on ~9% of calls. Those cells are retried once, and if they fail again
they stay missing (16 gold cells).

**Not done (credits):** a planned kimi check of 60 train/val deepseek answers (self-preference on the bulk set) got HTTP 402.

## Budget and coverage

OpenRouter returned **HTTP 402 (insufficient credits) at $44.55 logged spend**, below the $60 cap. Logged costs are from
`usage.cost`:

| Item | Calls | $ |
|---|---|---|
| attempts: gpt-6.1-sol / gemini / deepseek / minimax / qwen | 1,197 / 1,208 / 1,201 / 1,202 / 1,200 | 15.46 / 6.87 / 2.20 / 1.87 / 0.98 |
| judge ds-think (labels) / gpt-6.1-sol (sensitivity, gold) / kimi / ds / ds-strict | 4,728 / 1,409 / 160 / 750 / 100 | 7.50 / 7.51 / 1.23 / 0.18 / 0.07 |
| rubrics | 1,699 | 0.68 |
| **total** | | **44.55** |

Graded cells per model (no imputation; ungraded cells are simply absent from the fit):

| Model | train/val (of 511 items) | gold (of 150) |
|---|---|---|
| deepseek-v4.1-flash | 461 | 147 |
| qwen3.8-flash | 435 | 146 |
| minimax-m3.1-flash | 468 | 148 |
| gemini-3.8-flash | 423 | 147 |
| gpt-6.1-sol | 417 | 146 |

Gold eval: 734/750 cells, every one graded by the same ds-think judge. The 16 missing cells are double reasoning-budget
failures, not credit errors: all 750 gold answers exist. The routed-success table uses only the 140 gold tasks with all 5
cells graded, and the gold IRT b values use whatever cells exist (140 tasks with 5 cells, 6 with 4, 2 with 3, 2 with 2).

About $3 of attempts went to bugfix tasks that fell outside the final subset (the first full run was ordered by stratum and
stopped once the judge decision changed the budget). Coverage at the stop: gold has 734/750 cells graded, and 140 gold
tasks have all 5 graded. Train/val has **511 tasks with ≥ 1 graded cell** (330 with all 5, 95 with 4, 86 with 1–3) and
**2,204 graded cells**. 999 tasks were attempted, but about 2,170 answers are still ungraded. Finishing needs roughly $5.
Resume (from the repo root; failed or credit-error calls are retried, cached ones are skipped):

```sh
git checkout -- cards/openrouter-minimax-m3.1-flash.json cards/openrouter-gemini-3.8-flash.json cards/openrouter-gpt-6.1-sol.json  # link anchors on card means
.venv/bin/python scripts/outcomes/attempts.py attempt --workers 40
.venv/bin/python scripts/outcomes/attempts.py judge --judge ds-think --workers 32
.venv/bin/python scripts/outcomes/attempts.py validate --judge kimi --model openrouter-deepseek-v4.1-flash  # bulk self-preference check
.venv/bin/python scripts/outcomes/build_attempts.py --apply
```

## Fit

Persons are the 5 attempters and items are the 511 train/val tasks (gold is excluded from the fit). The held-out check
masks 15% of cells:

| Model | Held-out log-loss | AUC | Base-rate log-loss |
|---|---|---|---|
| **1PL (chosen)** | **0.406** | **0.877** | 0.622 |
| 2PL | 0.410 | 0.872 | 0.622 |

With 5 persons per item, discrimination isn't identifiable, so 1PL is used (a = 1). θ_IRT (se): qwen −2.25 (0.15),
minimax −1.82 (0.14), gemini −1.33 (0.14), deepseek −1.10 (0.13), gpt-6.1-sol +0.21 (0.13).
Train/val pass rates are deepseek .33, gemini .32, gpt-6.1-sol .55, minimax .24, qwen .21. Gold rates are .66, .61, .79, .45, .46.
219 items were failed by every model and 40 were passed by every model. Their b comes mostly from the N(0, 3²) prior, so
they clip at 10 or sit at the low end. Median item se is 1.28 on the router scale, and 143 items have se < 1.
**Weight by 1/se² or use `n_pass` in (0, n_models)** when using these items as training anchors.

## Mapping to the router 0..10 scale

`x_r = alpha + gamma·x`, the same construction as `REPORT.md`: gamma = median(a)/1.2 = **0.833** (1PL).
alpha is the **median over the 5 attempters** of (card mean θ over the 10 axes − gamma·θ_IRT), so it is robust to one bad
card: **alpha = 8.47, se 0.46** (bootstrap vs. median card se/√5), anchor residual MAD 0.47. The free Theil-Sen slope is
0.45 (95% CI −7.6..2.3): five anchors can't pin a slope, which is why it is fixed by the matcher's a.
The anchors are the cards being calibrated, so card deltas are **relative to the 5 cards' consensus**: the fit can say that
minimax is weaker than its card *relative to the others*, but not shift all five together.
Model θ on the router scale: qwen 6.59, minimax 6.95, gemini 7.36, deepseek 7.55, gpt-6.1-sol 8.64 (se 0.48 each).
Train/val `irt_b_router_scale` histogram over bins 1-2 … 9-10: 0/0/0/0/39/48/108/98/218. The 5 attempters span only
6.6–8.6, so difficulties below ~5 can't be resolved. Gold `irt_b_router_scale` (θ fixed, b fitted): median 7.1, range 5.2–10.

### Sensitivity: gpt-6.1-sol labels (138 train/val items, 609 cells graded by both)

| Model | card mean | ds-think labels | gpt-6.1-sol labels |
|---|---|---|---|
| deepseek-v4.1-flash | 6.09 | 8.00 | 6.07 |
| qwen3.8-flash | 6.59 | 7.09 | 5.63 |
| minimax-m3.1-flash | 7.59 | 7.24 | 6.14 |
| gemini-3.8-flash | 7.83 | 7.79 | 6.22 |
| gpt-6.1-sol | 8.44 | 8.76 | 8.86 |

Both judges agree that gpt-6.1-sol is clearly the strongest and that minimax and gemini are not above their cards. They
disagree on deepseek: gpt-6.1-sol passes 12% of its answers vs 40% under ds-think, and kimi sided with ds-think on gold.

## Card deltas (`card_deltas_attempts.json`, pre-apply snapshot; applied with `--apply`)

Each model gets one θ per skill axis. Items are grouped by the teacher's dominant skill axis, the item b values are held
fixed, and the prior is N(global θ, 1). An axis delta is applied only if all three hold: (1) n ≥ 25 items,
(2) |δ| > hypot(fit se, card se/2), and (3) the gpt-6.1-sol sensitivity fit puts the model on the same side of its card
mean (direction is robust to the judge). The updated se is min(card se, fit se). Provenance is
'verified (attempt-grade 2026-10)', recorded in `notes` and `sources`. The card `provenance` enum and `field_provenance`
stay unchanged because fewer than half the axes were fitted. `supersedes` is untouched.

| Card | Axis (n items): current → fitted ± se | Applied |
|---|---|---|
| openrouter-minimax-m3.1-flash | coding (70) 7.8→7.04±.55; debugging (71) 7.6→6.89±.54; math (27) 7.6→6.42±.62; reasoning (65) 7.7→6.81±.56 | **yes** |
| openrouter-gemini-3.8-flash | data_analysis (31) 7.7→6.92±.60; planning (37) 7.8→6.46±.62; reasoning (53) 7.9→6.99±.56 | **yes** |
| openrouter-gpt-6.1-sol | planning (37) 8.4→9.18±.56 | **yes** |
| openrouter-deepseek-v4.1-flash | 8 axes pass (1)+(2), +0.9..+2.5 (e.g. writing 6.0→8.47, debugging 6.1→7.56) | **no**: gpt-6.1-sol fit 6.07 ≈ card, so the direction isn't robust to the judge (and deepseek is the label judge) |
| openrouter-qwen3.8-flash | no axis passes (2) (card se 1.5) | no |

## Profiler evaluation: Spearman with the outcome IRT difficulty `irt_b`

v2 is `artifacts/panda-router-v2` (OnnxProfiler int8), using expected difficulty from text and context. Teacher is the
expected value of the teacher difficulty label. **v2 was trained on the train rows**, so only val and gold are held out for v2.

| Subset | n | v2 | teacher |
|---|---|---|---|
| train/val all | 511 | 0.418 | 0.409 |
| val only (v2 held-out) | 47 | 0.165 | 0.231 |
| **gold (held-out, WildChat)** | **150** | **0.109** | **0.421** |
| gold: chat_simple | 43 | 0.101 | 0.376 |
| gold: implementation | 18 | 0.711 | 0.804 |
| gold: docs_writing | 12 | 0.507 | 0.523 |
| gold: math_reasoning | 16 | −0.032 | 0.477 |
| gold: planning | 13 | −0.555 | 0.211 |
| gold: research | 9 | 0.387 | 0.213 |
| gold: data_analysis | 8 | −0.156 | 0.561 |
| train/val: bugfix / implementation / math / planning / research / docs | 105/65/34/37/36/33 | .48/.54/.63/.50/.48/.65 | .43/.50/.62/.48/.50/.56 |
| train/val: chat_simple / code_review / refactor | 37/37/22 | .02/−.42/.16 | −.09/−.43/.28 |

Per-category values for groups with n < 8 are omitted (`fit_attempts.json` has all of them). On held-out real user
prompts, v2's difficulty barely ranks real outcomes (0.11), while the teacher labels v2 was distilled from rank them at
0.42. The distillation loses most of the transferable difficulty signal outside the synthetic distribution. code_review is
anti-correlated for both, probably because "review this" tasks with long inputs look hard to the teacher but are easy to
pass under a checklist judge.

## True routed success on gold (pool = the 5 attempters, real graded outcomes, n = 140 tasks with all 5 graded)

Routing used v2 profiles. Cost is the logged attempt cost of the picked model.

| Policy | Success / 100 | $ per 100 tasks |
|---|---|---|
| v2, `cheapest_above_threshold` (default), cards before | 49.3 | 0.088 |
| v2, `max_utility`, cards before | 45.7 | 0.114 |
| v2, `max_quality` | 78.6 | 1.061 |
| v2, `cheapest_above_threshold`, cards after | 50.0 | 0.095 |
| always cheapest by card price (qwen3.8-flash) | 47.1 | 0.064 |
| always strongest by card (gpt-6.1-sol) | 78.6 | 1.061 |
| always deepseek / minimax / gemini | 67.9 / 45.7 / 60.7 | 0.148 / 0.114 / 0.474 |
| oracle: cheapest model that actually passed | 90.0 | 0.196 |

With the default mode, v2 is effectively "always qwen" (128/140 picks): +2 points over always-cheapest at 1.4× the cost,
and 29 points below always-strongest at 1/12 of the cost. Always-deepseek alone would reach 67.9 at $0.148. The gap to
the oracle (90 at $0.196) shows how much a profiler with better difficulty ranking could gain.

## Limitations

1. Single-turn and no tools. Many synthetic tasks reference repositories ("inspect `legacy/settle.cbl`"), so they test
   the plan and code a model writes blind. That is not agentic success, and it is not comparable to `REPORT.md`.
2. Labels come from one LLM judge (validated κ 0.85 against another LLM, not against humans). The bulk-set self-preference
   check was blocked by credits.
3. With only 5 attempters, items outside the 6.6–8.6 ability band are censored (219 all-fail, 40 all-pass).
4. Link location = consensus of the attempters' own cards, so absolute shifts of the whole ladder are invisible.
5. Coverage is partial (511 of 999 attempted train/val tasks graded) because of the credit stop.
