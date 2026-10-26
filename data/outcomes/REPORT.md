# Outcome-grounded coding difficulty and card calibration (2026-10-26)

Reproduce: `scripts/outcomes/fetch.py` (downloads into `data/outcomes/raw/`, git-ignored),
`scripts/outcomes/build.py` (fits, `tasks.jsonl`, `systems.jsonl`, `fit.json`, profiler eval),
`scripts/outcomes/cards.py [--apply]` (`card_deltas.json`, card edits). Code: `panda_router/outcomes/`.
Tests: `tests/test_outcomes.py`.

## Data and licences

| Source | Used for | Size | Licence / handling |
|---|---|---|---|
| github.com/swe-bench/experiments (`evaluation/*/*/results/results.json`, `per_instance_details.json`, `metadata.yaml`) | outcomes, component A | 297 submissions with per-instance lists: verified 175, lite 84, full test 24, multilingual 14 (multimodal 12 more, excluded below) | **No licence file.** Resolved lists are used as outcome facts only; raw files are not redistributed. |
| princeton-nlp/SWE-bench (test), _Verified, _Lite; SWE-bench/SWE-bench_Multilingual | task text (`problem_statement`) | 2,294 / 500 / 300 / 300 | MIT (SWE-bench repo; Multilingual card says MIT). Issue text comes from public GitHub issues of each repo. |
| ibragim-bad/swe_rebench_07_2026_trajectories | outcomes, component B (systems/cards only) | 17 systems × 5 runs × 111 tasks = 9,434 graded runs (1 skipped) | **"other"** (does not relicense). Approved by the architect for **resolved flags only**: no task text or trajectories are used or written anywhere. Only `(instance, participant, run, status, resolved)` is kept (`raw/rebench07_outcomes.jsonl`); every shard is deleted after it is read. |

Skipped: SWE-bench Multimodal (12 systems, 510 tasks). It shares no system or task with the other splits, so
its scale can't be linked. Early multimodal entries also only report counts. The SWE-rebench leaderboard parquets (CC-BY-4.0) do
not contain the 111 July-2026 tasks, so component B has no licensable task text. LiveCodeBench, Aider polyglot
and Multi-SWE-bench were not added in this pass: there are no per-instance multi-system result files in a
licence-clean form that could be fetched quickly. The older Nebius anchors (`data/gold/anchors.jsonl`) are left unchanged.

## Fit

Model: binomial MAP IRT, `logit P = a_i (theta_s - b_i)`, theta ~ N(0,1), b ~ N(0,3²), log a ~ N(0,0.5²)
(`panda_router/outcomes/irt.py`). Systems are persons and tasks are items. The two components share neither, so each is fitted on its own.

- **A (SWE-bench):** verified + lite + full test are linked through shared instance ids. Multilingual is linked by
  renaming its 13 mini-swe-agent v2 runs to the verified mini-swe-agent v2 run of the same model
  (`fit.json: multilingual_linked_systems`). This assumes ability carries across languages and that the
  `-high` effort variants match. 284 systems, 2,594 tasks, 171,956 graded (system, task) cells.
- **B (rebench07):** 17 systems, 111 tasks (go/java/python/rust/typescript), 1,887 cells, 9,434 runs.

Held-out diagnostics (10% of cells masked at random, refit, then scored on the masked trials):

| Component | Model | Held-out log-loss | AUC | Base-rate log-loss |
|---|---|---|---|---|
| A | 1PL | 0.282 | 0.949 | 0.671 |
| A | **2PL** (chosen) | **0.270** | **0.954** | 0.671 |
| B | 1PL | 0.384 | 0.904 | 0.692 |
| B | **2PL** (chosen) | **0.370** | **0.912** | 0.692 |

The median item discrimination a is 1.25 in A and 1.26 in B.

## Mapping to the router 0..10 scale

The matcher computes `P = sigmoid(1.2 (theta_r - b_r))`. With the linear map `x_r = alpha + gamma·x`, a typical item agrees
with the matcher when `1.2·gamma = median(a)`. So **gamma = median(a)/1.2** (1.041 in A, 1.047 in B): one logit
of IRT ability is one logit in the matcher. **alpha** is the median over anchor systems of
`card coding theta − gamma·theta_irt`. Anchors are common-scaffold systems running the card's exact base model;
fine-tunes and vendor agent products are excluded. The `alpha` se is the larger of the bootstrap se and
median(card se)/√n. Since gamma > 0, the map is monotone (`scale.to_router`, tested). `irt_b_router_scale`
clips it to 1..10; `irt_b_router` keeps the unclipped value.

| Component | Anchors (system → card, card θ) | alpha | alpha se | Anchor residual MAD | Theil-Sen free slope (diagnostic) |
|---|---|---|---|---|---|
| A | openhands Qwen3-Coder-30B-A3B → ollama-qwen3-coder-30b (5.8); mini devstral-small-2512 → ollama-devstral-small-2-24b (6.0) | 6.33 | **1.06** (two `estimated` cards) | 0.06 | n/a (<3 anchors) |
| B | deepseek-v4-pro (6.9), gpt-5.6-luna (7.4), grok-4.5 (7.7), minimax-m3 (6.7), qwen3.6-27b (6.4), qwen3.6-35b-a3b (6.1) | 7.75 | 0.35 | 0.28 | 0.58 (95% CI −0.45..1.27) |

The free Theil-Sen slope has a CI that includes the discrimination-matched slope. Six hand-set cards can't pin
a slope, which is why the slope is fixed by the matcher's a.

**Caveat:** A's location rests on two `estimated` local-model cards. Its router-scale values are reasonable
(below), but read them ±1. Rankings within A (`irt_b`) do not depend on the location.

Sanity check, A, median theta_router per base model: gpt-4o 4.7, claude-sonnet-3.5 5.7, o3 6.2, claude-sonnet-4 7.0,
gpt-5 7.2, gpt-5.2 7.3, glm-5 7.4, claude-opus-4.6 7.7, claude-opus-4.5 7.9. B: qwen3.5-35b 5.1 … fable-5 8.9.

### Scaffold effects (same base model, different agent)

- A, base models with ≥3 submissions (router-scale theta): claude-sonnet-3.5 n=30, range 4.5–6.4 (sd 0.54);
  gpt-4o n=26, 3.9–5.5 (0.42); claude-sonnet-4 n=12, 6.1–7.6 (0.41); claude-sonnet-3.7 n=5, 3.2–6.7 (1.43);
  gemini-3-pro n=3, 3.4–7.8 (2.46); claude-opus-4.5 n=5, 7.7–8.3 (0.23). The median within-model sd is **0.41**.
  It is added in quadrature to every card se.
- B, vendor agent vs. the same model in the common scaffold: Claude Code (fable-5) 8.69 vs. 8.92; Codex
  (gpt-5.6-sol) 8.18 vs. 8.44; Junie (grok-4.5) 8.57 vs. 8.63. The vendor products did *not* beat the
  common scaffold on this set.

## Outputs

- `tasks.jsonl`: 2,594 SWE-bench tasks (component A only). Fields: `id, raw_id, source, repo, text`
  (`"Repository: <repo>\n\n<problem_statement>"`, same format as gold), `irt_b, irt_a, se, irt_b_router,
  irt_b_router_scale, se_router, n_systems, licence`. By source: test-only 1,587 (24 systems, 2023–25),
  test+verified 407, multilingual 300, lite+test 207, lite+test+verified 93. The median `se_router` is 0.73.
  Histogram of `irt_b_router_scale` over bins 1-2 … 9-10: 4 / 112 / 208 / 293 / 307 / 278 / 232 / 240 / 920.
  115 tasks are clipped at 10, mostly test-only tasks that no 2023–25 system solved. **Weight training anchors by
  `1/se_router²` or filter `n_systems >= 100`** (707 tasks).
- `systems.jsonl`: 301 systems (284 A + 17 B) with `base_model, agent, kind, theta_irt, se_irt,
  theta_router, se_router, exact_card, successor_card, licence`.
- `fit.json`: diagnostics, link, anchors, and the profiler evaluation. `card_deltas.json`: card proposals with and without rebench07.

**Gold overlap: none.** All 2,594 tasks were checked against the 285 `data/gold/gold.jsonl` rows by normalised text
(lowercase alphanumeric tokens), by `raw_id`, and by containment of the first 400 normalised characters of the problem
body. There were 0 hits, so nothing was dropped. Gold is SWE-rebench / SWE-smith / WildChat, which is disjoint from SWE-bench.

## Card calibration

Evidence is router-scale theta, with se = hypot(fit+link se, scaffold sd 0.41). **Exact** means the card's exact model
appears in a common scaffold. **Lower bound** means a predecessor appears (from `scale.PREDECESSOR`, or from another card's
`supersedes`), and a successor is assumed to be at least as strong. Rules applied: an exact model with ≥100 tasks sets coding θ to the fitted value and shifts
every axis by the same delta. Coding and debugging se are set to the fitted se. `skills` becomes `verified` only for
API-served exact models. Local Ollama cards run a Q4 quant, so their delta is applied only if |δ| ≥ 0.15 and provenance stays as it was.
A lower bound is applied only if the violation exceeds its se (none did). `supersedes` fields are untouched.
B's anchors are these same exact cards, so the B deltas are **relative to their consensus** (they sum to ≈0).

| Card | Evidence | Systems | Current θ | Without rebench07 (A only) | With rebench07 | δ applied | Provenance |
|---|---|---|---|---|---|---|---|
| grok-4.5 | exact (B) | grok-4.5 | 7.7 | n/a | 8.63 ± 0.54 | **+0.9** | → verified |
| openrouter-minimax-m3 | exact (B) | minimax-m3 | 6.7 | n/a | 7.37 ± 0.54 | **+0.7** | → verified |
| codex-gpt-5.6-luna | exact (B) | gpt-5.6-luna (swelike, medium) | 7.4 | n/a | 7.21 ± 0.54 | **−0.2** | → verified |
| openrouter-deepseek-v4-pro | exact (B) | deepseek-v4-pro | 6.9 | n/a | 6.91 ± 0.54 | 0.0 (se 0.7→0.54) | → verified |
| ollama-qwen3.6-35b | exact (B), Q4 local | qwen3.6-35b-a3b | 6.1 | n/a | 5.73 ± 0.55 | **−0.4** | estimated (kept) |
| ollama-qwen3.6-27b | exact (B), Q4 local | qwen3.6-27b | 6.4 | n/a | 6.39 ± 0.54 | none (<0.15) | kept |
| ollama-devstral-small-2-24b | exact (A anchor) | mini devstral-small-2512 | 6.0 | 6.06 ± 1.14 | same | none (anchor, circular) | kept |
| ollama-qwen3-coder-30b | exact (A anchor) | openhands Qwen3-Coder-30B | 5.8 | 5.74 ± 1.14 | same | none (anchor, circular) | kept |
| grok-4.6 | ≥ grok-4.5 (supersedes) | grok-4.5 | 8.4 | n/a | ≥ 8.63 ± 0.54 | none (violation 0.2 < se); **note: now below grok-4.5** | kept |
| openrouter-glm-5.3 | ≥ glm-5.2 | glm-5.2 | 8.0 | n/a | ≥ 8.43 ± 0.54 | none (0.4 < se) | kept |
| openrouter-gpt-6-sol | ≥ gpt-5.6-sol | gpt-5.6-sol | 8.2 | n/a | ≥ 8.44 ± 0.54 | none (0.2 < se) | kept |
| claude-opus-5.5 / fable-5.1 / sonnet-5.5 | ≥ opus-5 / fable-5 / sonnet-5 | | 9.3 / 9.0 / 8.6 | n/a | ≥ 8.82 / 8.92 / 8.07 | consistent | kept |
| codex-gpt-6-luna, ollama-qwen3.8-27b, openrouter-mimo-v2.6-pro | ≥ predecessor | | 7.7 / 6.7 / 8.1 | n/a | ≥ 7.21 / 6.39 / 7.34 | consistent | kept |
| glm-4.7 | ≥ glm-4.6 (A) | zai glm-4.6 | 6.5 | ≥ 6.47 ± 1.14 | same | consistent | kept |
| openrouter-gemini-3.8-flash | ≥ gemini-3.5-flash (A) | mini gemini-3.5-flash | 8.0 | ≥ 7.23 ± 1.14 | same | consistent | kept |

Without rebench07, no card changes: A has only two exact anchors, and both define the location. Every applied
change comes from rebench07. That is one benchmark of 111 tasks in one common scaffold, which is why se was not narrowed below 0.54.
Re-running `build.py` after `--apply` reuses the updated cards as B anchors. alpha moves by less than 0.1, because the applied cards now sit on
their fitted values. `card_deltas.json` is the pre-apply snapshot.

## Profiler baseline (what v2 must beat)

Spearman of expected difficulty against `irt_b` on the 2,594 tasks. Input is the issue text only, with context
`{requires_tools: true, has_images: false}`; patch-derived context is not used (RESULTS.md limitation 4). The 95% CI is a bootstrap.

| Profiler | All (n=2,594) | 95% CI | verified | lite | multilingual | n_systems ≥ 100 (n=707) | se_router < 0.5 (n=907) |
|---|---|---|---|---|---|---|---|
| v1 (`artifacts/panda-router-v1`, int8 ONNX) | **0.046** | 0.009..0.080 | 0.112 | 0.021 | 0.048 | 0.061 | 0.091 |
| heuristic | 0.006 | −0.031..0.043 | 0.080 | −0.017 | 0.048 | 0.029 | 0.121 |

This confirms limitation 1 at 28× the sample size: teacher-distilled difficulty barely ranks real SWE outcome
difficulty. v1's expected difficulty is also compressed (mean 4.83, sd 0.64), while the outcome scale's median is 7.4.
A v2 trained with `tasks.jsonl` anchors should be judged on held-out repos with these columns; the per-task values are in
`raw/profiler_eval.csv`.
