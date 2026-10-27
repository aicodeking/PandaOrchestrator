# Panda Router GOLD set (held out, real tasks only)

`gold.jsonl` is the held-out evaluation set for the task profiler. **Never train on it.** Each line
follows `schemas/CONTRACTS.md` ("Labelled example"), with `meta.split = "gold"`.

## Sources and licences

| source | dataset | licence | what we use |
|---|---|---|---|
| swe-rebench | `nebius/SWE-rebench` (`test` split, 21,336 instances) | CC-BY-4.0 (repo code keeps its own licence; `meta.repo_license`) | `problem_statement` as the task, `patch` only to count files for `context.files_in_scope` |
| swe-smith | `SWE-bench/SWE-smith` (train shards 0-1) | MIT | `problem_statement` (LLM-written issue for a synthetic bug in a real repo) |
| wildchat | `allenai/WildChat-1M` (train shards 0-7) | ODC-BY | first user turn of English, non-toxic, non-redacted conversations |
| anchors | `nebius/SWE-rebench-openhands-trajectories`, `nebius/SWE-agent-trajectories` | CC-BY-4.0 | only the per-instance outcome columns (`resolved` / `target`) |

Raw downloads live in `data/gold/raw/` (gitignored-size parquet files; only the outcome columns of
the trajectory datasets were downloaded).

## GOLD partition rule

A raw record belongs to the gold partition iff `int(sha1(id).hexdigest(), 16) % 10 == 0`, where
`id` is `instance_id` (SWE-rebench, SWE-smith) or `conversation_hash` (WildChat). The training data
builder (`panda_router/datagen/common.py::is_gold_reserved`) excludes exactly these records, and
`build_gold.py select` asserts every selected record satisfies the rule. Gold ids are
`gold-{reb,smi,wil}-<sha1(raw_id)[:10]>`; the raw id is kept in `meta.raw_id`.

## Selection

- **SWE-rebench (120)**: gold-partition instances that have published agent outcomes (so they can be
  anchored, see below), one per repository first, `problem_statement` 80..20k chars.
- **SWE-smith (25)**: gold-partition instances, at most 2 per repo, no near-duplicate statements.
- **WildChat (215)**: gold-partition first turns -> keyword buckets per taxonomy category -> a cheap
  LLM screen (Kimi, Codex as fallback when Kimi hit its quota; `wildchat_screen.jsonl`) that only
  decides keep/drop and a rough category for balancing -> up to 20 per screened category (8 bugfix,
  14 implementation, because SWE sources already cover code). The screen is not a label.
- PII: emails, credentials, API keys, IPs and phone numbers are masked (datagen `scrub_pii`,
  aggressive mode for chats), plus user names inside home-directory paths. WildChat conversations
  flagged `redacted` or `toxic` are excluded.
- Context fields mirror the training builder: SWE tasks get `repo_languages=["python"]`,
  `files_in_scope` = files in the gold patch, `requires_tools=true`; chats get only
  `estimated_input_tokens`.

## Labelling

Same label prompt, answer cleaning and soft-label merge as the training data
(`panda_router/datagen/label.py`, `merge.py`), prefixed with an instruction to think carefully
because the labels form a held-out gold set. Batches of 5 tasks per call. Each teacher labels
independently:

- `codex`: `codex exec --skip-git-repo-check -m gpt-5.6-luna`
- `grok`: `grok -m grok-4.7-build-fast --disable-web-search -p` (added when Kimi hit its quota)
- `ollama`: local `gemma4:26b`, `format=json`, `think=false`, temperature 0.2 (extra teacher where
  available; the GPU was shared with other jobs, so it did not cover every task)
- `kimi`: `kimi -p` (returned HTTP 429 "5-hour usage limit" for the whole labelling window)

Per-teacher raw and cleaned answers: `teacher_answers.jsonl`; raw CLI outputs:
`cache/calls/<teacher>/`. In `gold.jsonl`, `meta.teacher_answers` holds each teacher's point answer,
`meta.teachers` the families used and `meta.agreement` the mean pairwise agreement (datagen
definition: mean of category match, 1-|Δdiff|/9, 1-mean|Δskill|/10 and matching flag+checklist bits).
Soft labels: category = mean of teacher one-hots (0.75/0.25 when a teacher names a secondary),
ordinal fields = mean of σ=0.6 discretised Gaussians around each teacher's point, flags/checklist =
mean of 0/1 answers, `out_tokens_log10` = mean of log10 answers.

## Status and statistics (2026-10-25)

- **285 tasks** in `gold.jsonl` (of 360 candidates); a task is kept only with >= 2 teacher families.
  By source: swe-rebench 92, swe-smith 23, wildchat 170. Teacher sets: codex+ollama 205,
  codex+grok 55, codex+grok+ollama 25. The other 75 candidates only have a Codex answer. They stay in
  `candidates.jsonl` / `teacher_answers.jsonl` and can be merged later
  (`build_gold.py label ...; build_gold.py merge`).
- Teacher availability during labelling: Codex covered all 360. Kimi returned HTTP 429 ("5-hour usage
  limit") the whole time, so it has no gold answers. Grok returned HTTP 402 ("usage balance exhausted")
  after 80 tasks. Ollama gemma4:26b (thinking off) covered 230 tasks; the GPU was shared.
- Top category (argmax of the soft label): bugfix 102, chat_simple 48, implementation 37,
  planning 17, math_reasoning 15, research 11, docs_writing 11, refactor 10, data_analysis 9,
  ui_frontend 8, code_review 7, devops_infra 5, test_writing 5. Real data is skewed: the SWE sources
  are almost all bugfixes. The teachers often relabel screened WildChat "research" or "docs" prompts as
  chat_simple.
- Expected difficulty: mean 4.22. Rounded histogram: 1:9, 2:34, 3:66, 4:54, 5:63, 6:51, 7:8.
- Mean per-task agreement (datagen definition): 0.884.

Pairwise teacher agreement (`agreement.json`):

| pair | n | category agree (kappa) | difficulty Spearman | difficulty MAE | within ±1 | skill MAE | flags agree | checklist agree |
|---|---|---|---|---|---|---|---|---|
| codex~grok | 80 | 0.89 (0.86) | 0.86 | 0.69 | 0.88 | 0.55 | 0.93 | 0.93 |
| codex~ollama | 230 | 0.78 (0.73) | 0.80 | 0.84 | 0.84 | 0.70 | 0.87 | 0.89 |
| grok~ollama | 25 | 0.88 (0.84) | 0.86 | 0.68 | 0.92 | 0.68 | 0.91 | 0.91 |

## Outcome anchors (PLAN.md 12.4 #1): `anchors.jsonl`, `anchor_report.json`

**Data found.** Nebius, the SWE-rebench authors, publish per-instance agent outcomes under
CC-BY-4.0:
- `nebius/SWE-rebench-openhands-trajectories`: Qwen3-Coder-480B with OpenHands, 67,074 runs on 6,306
  instances (~10 runs each).
- `nebius/SWE-agent-trajectories`: SWE-agent with Llama-3.1 8B/70B/405B policies, 80,036 runs on
  3,591 SWE-bench-extra instances. Instance ids are shared with SWE-rebench.

The SWE-rebench leaderboard dataset (`nebius/SWE-rebench-leaderboard`) has tasks but no outcomes.
The frontier leaderboard trajectories (`ibragim-bad/swe_rebench_07_2026_trajectories`: 17 systems × 5
runs × 111 tasks) are licensed "other" and cover none of our partition, so they were **not used**.

**Fit.** A 1PL (Rasch) model with binomial counts, MAP with priors b ~ N(0, 2²) and θ ~ N(0, 3²),
over all 8,694 instances (10,525 model×instance cells, 147,110 runs). A 2PL is not identifiable with
only 4 distinct models, so it was not fitted. `difficulty_1_10` is a linear rescale of b: the 2nd–98th
percentile maps to 1..10. Caveats:
- This is effectively a 1–2 model ladder of 2025-era open models, not a frontier ladder.
- 54% of the 92 anchored gold instances failed in every run (12% passed in every run), so b is
  saturated at both ends.
- Instances seen only by Llama connect to the Qwen scale only through the 18 shared instances and the
  prior.

**Reality check (n = 92 gold SWE-rebench tasks).**

| difficulty source | Spearman vs IRT b |
|---|---|
| merged teacher soft label (expected level) | **0.00** (bootstrap 95% CI −0.21..0.22) |
| codex alone (n=92) / grok (n=27) / ollama (n=73) | 0.09 / 0.01 / −0.14 |
| SWE-rebench's own `llm_score.difficulty_score` | 0.24 |
| merged teacher vs Qwen fail rate (72 instances with Qwen runs) | 0.04 |

The teachers agree with each other (ρ ≈ 0.80–0.86) but do **not** predict empirical agent
difficulty on real SWE issues. Teacher difficulty labels should be treated as "perceived difficulty".
Calibrating them against outcomes (PLAN 12.4 #1) is needed before difficulty can mean "which tier
succeeds".


## Reproduce

```bash
.venv/bin/python scripts/eval/build_gold.py select
.venv/bin/python scripts/eval/build_gold.py label --teachers codex grok ollama kimi
.venv/bin/python scripts/eval/build_gold.py merge          # gold.jsonl + agreement.json
.venv/bin/python scripts/eval/build_gold.py validate
.venv/bin/python scripts/eval/fit_anchors.py               # anchors.jsonl + anchor_report.json
```

## v2 changes (2026-10-26)

- SWE `files_in_scope` / `estimated_input_tokens` now derive from the issue text only (no patch info). Spearman with `multi_file`: 0.87 -> 0.11.
- `gold-wil-b090490cce` dropped (normalised text duplicated a train row); SWE rows carry `meta.repo_in_train`.
- Grok (402 balance exhausted) and Kimi (5h limit) were unavailable; DeepSeek (opencode free) labelled 45 more rows before its limit, so gold has 329 rows and 45 rows use codex+deepseek. Ollama answers are kept as an extra.

## v3 relabel (DeepSeek V4.1 Flash)

All candidates were labelled with `deepseek/deepseek-v4.1-flash` (OpenRouter), so every gold row has codex + deepseek
(79 also grok). gemma4 answers are kept in `meta.teacher_answers` as extras but are no longer merged into the soft labels
(`gold.EXTRA_TEACHERS`). Rows 329 -> 359 (one candidate dropped as a train duplicate), mean agreement 0.889 -> 0.909,
codex~deepseek category agreement 0.844 (kappa 0.81), difficulty Spearman 0.866. Per-pair stats: `agreement.json`.
