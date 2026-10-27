# Panda Router training data: statistics

Generated 2026-10-26 14:28 by `scripts/datagen/run.py build`. Format: `schemas/CONTRACTS.md`.

## Totals

- Labelled records: **8247** (originals 7170, minimal pairs 1077)
- Real-seed share of originals: **50.9%** (3646/7170)
- Splits: train 7015, val 629, test 603
- Records with a third (Ollama gemma4:26b) opinion: 167
- Mean per-record agreement (meta.agreement, over full-label teachers): 0.897
- Minimal pairs labelled by a single teacher (meta.single_teacher=true, kept so pairs reach the target): 0
- Records per full-label teacher set: codex+deepseek 5046, codex+grok+deepseek 3004, codex+kimi+deepseek 97, codex+kimi+grok+deepseek 100
- Near-duplicates dropped (cos > 0.95): 104; clusters: 1049; pool tasks not (yet) labelled by enough teachers (excluded): 404

## Per source

| key | n | % |
|---|---|---|
| synthetic | 3524 | 42.7 |
| wildchat | 1504 | 18.2 |
| swe-rebench | 1318 | 16.0 |
| minimal-pair | 1077 | 13.1 |
| swe-smith | 824 | 10.0 |

## Per source incl. minimal-pair origin

| key | n | % |
|---|---|---|
| synthetic | 3524 | 42.7 |
| wildchat | 1504 | 18.2 |
| swe-rebench | 1318 | 16.0 |
| swe-smith | 824 | 10.0 |
| minimal-pair(synthetic) | 381 | 4.6 |
| minimal-pair(wildchat) | 278 | 3.4 |
| minimal-pair(swe-rebench) | 253 | 3.1 |
| minimal-pair(swe-smith) | 165 | 2.0 |

## Per split and source

| split | minimal-pair | swe-rebench | swe-smith | synthetic | wildchat |
|---|---|---|---|---|---|
| train | 922 | 1062 | 782 | 3009 | 1240 |
| val | 91 | 136 | 42 | 195 | 165 |
| test | 64 | 120 | 0 | 320 | 99 |

## Per primary category (argmax of soft label)

| key | n | % |
|---|---|---|
| bugfix | 2992 | 36.3 |
| implementation | 1422 | 17.2 |
| chat_simple | 676 | 8.2 |
| planning | 617 | 7.5 |
| docs_writing | 461 | 5.6 |
| code_review | 414 | 5.0 |
| research | 402 | 4.9 |
| data_analysis | 321 | 3.9 |
| math_reasoning | 253 | 3.1 |
| test_writing | 212 | 2.6 |
| refactor | 185 | 2.2 |
| ui_frontend | 152 | 1.8 |
| devops_infra | 140 | 1.7 |

## Per difficulty (rounded expected difficulty of the final soft label)

| key | n | % |
|---|---|---|
| 5 | 1536 | 18.6 |
| 6 | 1534 | 18.6 |
| 7 | 1296 | 15.7 |
| 4 | 1202 | 14.6 |
| 3 | 906 | 11.0 |
| 8 | 888 | 10.8 |
| 2 | 447 | 5.4 |
| 9 | 326 | 4.0 |
| 1 | 86 | 1.0 |
| 10 | 26 | 0.3 |

## Teacher agreement (raw point answers, per teacher pair)

Teachers: deepseek = deepseek/deepseek-v4.1-flash (OpenRouter), codex = gpt-5.6-luna, kimi = Kimi CLI default, grok = grok-4.7-build-fast, ollama = gemma4:26b (tie-break: category + difficulty only).

### codex vs deepseek

- n = 8247
- Primary category accuracy: **0.846**
- Difficulty Spearman: **0.8974**, MAE 0.768, means {'codex': 5.8, 'deepseek': 5.37}
- Strong disagreement (|Δdiff| ≥ 3 or different primary category) rate: 0.1639
- Flag Cohen's κ mean: **0.745**; checklist κ mean: 0.734
- out_tokens (log10) Spearman: 0.8916

| flag | κ |
|---|---|
| needs_tools | 0.876 |
| needs_vision | 0.938 |
| long_context | 0.932 |
| needs_review | 0.654 |
| ambiguous_spec | 0.488 |
| multi_file | 0.617 |
| needs_web | 0.71 |

| checklist id | κ |
|---|---|
| edits_code | 0.842 |
| touches_gt3_files | 0.707 |
| new_feature | 0.834 |
| has_failing_behavior | 0.907 |
| needs_root_cause | 0.765 |
| needs_run_commands | 0.868 |
| needs_browser_or_web | 0.69 |
| has_images | 0.935 |
| input_gt_50k_tokens | 0.983 |
| concurrency_or_distributed | 0.818 |
| security_sensitive | 0.791 |
| formal_math_or_proof | 0.736 |
| domain_expertise | 0.57 |
| clear_acceptance_criteria | 0.365 |
| undefined_terms | 0.487 |
| design_decisions | 0.605 |
| visual_ui_work | 0.831 |
| writes_prose | 0.785 |
| data_processing | 0.735 |
| infra_config | 0.834 |
| multi_step_plan | 0.65 |
| reviews_existing_work | 0.539 |
| trivial_one_liner | 0.653 |
| high_stakes | 0.689 |

| skill axis | Spearman |
|---|---|
| coding | 0.844 |
| debugging | 0.925 |
| reasoning | 0.89 |
| math | 0.803 |
| writing | 0.866 |
| research | 0.76 |
| review | 0.825 |
| planning | 0.89 |
| ui_frontend | 0.87 |
| data_analysis | 0.827 |

### grok vs deepseek

- n = 3104
- Primary category accuracy: **0.8766**
- Difficulty Spearman: **0.8916**, MAE 0.532, means {'grok': 4.93, 'deepseek': 5.0}
- Strong disagreement (|Δdiff| ≥ 3 or different primary category) rate: 0.1266
- Flag Cohen's κ mean: **0.758**; checklist κ mean: 0.748
- out_tokens (log10) Spearman: 0.9068

| flag | κ |
|---|---|
| needs_tools | 0.892 |
| needs_vision | 0.91 |
| long_context | 0.946 |
| needs_review | 0.644 |
| ambiguous_spec | 0.591 |
| multi_file | 0.584 |
| needs_web | 0.738 |

| checklist id | κ |
|---|---|
| edits_code | 0.875 |
| touches_gt3_files | 0.484 |
| new_feature | 0.823 |
| has_failing_behavior | 0.922 |
| needs_root_cause | 0.716 |
| needs_run_commands | 0.883 |
| needs_browser_or_web | 0.738 |
| has_images | 0.904 |
| input_gt_50k_tokens | 0.982 |
| concurrency_or_distributed | 0.84 |
| security_sensitive | 0.824 |
| formal_math_or_proof | 0.728 |
| domain_expertise | 0.508 |
| clear_acceptance_criteria | 0.499 |
| undefined_terms | 0.471 |
| design_decisions | 0.719 |
| visual_ui_work | 0.787 |
| writes_prose | 0.786 |
| data_processing | 0.766 |
| infra_config | 0.848 |
| multi_step_plan | 0.711 |
| reviews_existing_work | 0.7 |
| trivial_one_liner | 0.694 |
| high_stakes | 0.734 |

| skill axis | Spearman |
|---|---|
| coding | 0.872 |
| debugging | 0.929 |
| reasoning | 0.873 |
| math | 0.702 |
| writing | 0.846 |
| research | 0.63 |
| review | 0.732 |
| planning | 0.839 |
| ui_frontend | 0.876 |
| data_analysis | 0.799 |

### codex vs grok

- n = 3104
- Primary category accuracy: **0.8734**
- Difficulty Spearman: **0.8893**, MAE 0.828, means {'codex': 5.45, 'grok': 4.93}
- Strong disagreement (|Δdiff| ≥ 3 or different primary category) rate: 0.1372
- Flag Cohen's κ mean: **0.816**; checklist κ mean: 0.756
- out_tokens (log10) Spearman: 0.9135

| flag | κ |
|---|---|
| needs_tools | 0.948 |
| needs_vision | 0.939 |
| long_context | 1.0 |
| needs_review | 0.707 |
| ambiguous_spec | 0.529 |
| multi_file | 0.874 |
| needs_web | 0.717 |

| checklist id | κ |
|---|---|
| edits_code | 0.904 |
| touches_gt3_files | 0.575 |
| new_feature | 0.811 |
| has_failing_behavior | 0.925 |
| needs_root_cause | 0.754 |
| needs_run_commands | 0.941 |
| needs_browser_or_web | 0.695 |
| has_images | 0.965 |
| input_gt_50k_tokens | 1.0 |
| concurrency_or_distributed | 0.861 |
| security_sensitive | 0.882 |
| formal_math_or_proof | 0.714 |
| domain_expertise | 0.439 |
| clear_acceptance_criteria | 0.633 |
| undefined_terms | 0.435 |
| design_decisions | 0.662 |
| visual_ui_work | 0.845 |
| writes_prose | 0.856 |
| data_processing | 0.763 |
| infra_config | 0.811 |
| multi_step_plan | 0.64 |
| reviews_existing_work | 0.639 |
| trivial_one_liner | 0.634 |
| high_stakes | 0.761 |

| skill axis | Spearman |
|---|---|
| coding | 0.865 |
| debugging | 0.926 |
| reasoning | 0.878 |
| math | 0.764 |
| writing | 0.869 |
| research | 0.679 |
| review | 0.732 |
| planning | 0.867 |
| ui_frontend | 0.877 |
| data_analysis | 0.804 |

### codex vs kimi

- n = 197
- Primary category accuracy: **0.8274**
- Difficulty Spearman: **0.9143**, MAE 1.249, means {'codex': 6.04, 'kimi': 4.85}
- Strong disagreement (|Δdiff| ≥ 3 or different primary category) rate: 0.198
- Flag Cohen's κ mean: **0.706**; checklist κ mean: 0.693
- out_tokens (log10) Spearman: 0.9135

| flag | κ |
|---|---|
| needs_tools | 0.919 |
| needs_vision | 1.0 |
| long_context | 1.0 |
| needs_review | 0.553 |
| ambiguous_spec | 0.14 |
| multi_file | 0.531 |
| needs_web | 0.799 |

| checklist id | κ |
|---|---|
| edits_code | 0.826 |
| touches_gt3_files | 0.517 |
| new_feature | 0.777 |
| has_failing_behavior | 0.939 |
| needs_root_cause | 0.748 |
| needs_run_commands | 0.919 |
| needs_browser_or_web | 0.75 |
| has_images | 0.969 |
| input_gt_50k_tokens | 1.0 |
| concurrency_or_distributed | 0.722 |
| security_sensitive | 0.816 |
| formal_math_or_proof | 0.644 |
| domain_expertise | 0.507 |
| clear_acceptance_criteria | 0.614 |
| undefined_terms | 0.163 |
| design_decisions | 0.488 |
| visual_ui_work | 0.858 |
| writes_prose | 0.733 |
| data_processing | 0.588 |
| infra_config | 0.797 |
| multi_step_plan | 0.45 |
| reviews_existing_work | 0.575 |
| trivial_one_liner | 0.552 |
| high_stakes | 0.688 |

| skill axis | Spearman |
|---|---|
| coding | 0.833 |
| debugging | 0.905 |
| reasoning | 0.886 |
| math | 0.747 |
| writing | 0.851 |
| research | 0.742 |
| review | 0.739 |
| planning | 0.868 |
| ui_frontend | 0.861 |
| data_analysis | 0.752 |

### kimi vs grok

- n = 100
- Primary category accuracy: **0.87**
- Difficulty Spearman: **0.9254**, MAE 0.7, means {'kimi': 4.93, 'grok': 5.55}
- Strong disagreement (|Δdiff| ≥ 3 or different primary category) rate: 0.13
- Flag Cohen's κ mean: **0.742**; checklist κ mean: 0.737
- out_tokens (log10) Spearman: 0.9558

| flag | κ |
|---|---|
| needs_tools | 0.98 |
| needs_vision | 1.0 |
| long_context | 1.0 |
| needs_review | 0.627 |
| ambiguous_spec | 0.286 |
| multi_file | 0.434 |
| needs_web | 0.864 |

| checklist id | κ |
|---|---|
| edits_code | 0.88 |
| touches_gt3_files | 0.592 |
| new_feature | 0.798 |
| has_failing_behavior | 0.9 |
| needs_root_cause | 0.657 |
| needs_run_commands | 0.98 |
| needs_browser_or_web | 0.864 |
| has_images | 1.0 |
| input_gt_50k_tokens | 1.0 |
| concurrency_or_distributed | 0.805 |
| security_sensitive | 0.872 |
| formal_math_or_proof | 0.521 |
| domain_expertise | 0.723 |
| clear_acceptance_criteria | 0.584 |
| undefined_terms | 0.265 |
| design_decisions | 0.609 |
| visual_ui_work | 0.864 |
| writes_prose | 0.732 |
| data_processing | 0.775 |
| infra_config | 0.742 |
| multi_step_plan | 0.559 |
| reviews_existing_work | 0.668 |
| trivial_one_liner | 0.595 |
| high_stakes | 0.7 |

| skill axis | Spearman |
|---|---|
| coding | 0.864 |
| debugging | 0.912 |
| reasoning | 0.929 |
| math | 0.798 |
| writing | 0.905 |
| research | 0.65 |
| review | 0.774 |
| planning | 0.894 |
| ui_frontend | 0.81 |
| data_analysis | 0.796 |

### DeepSeek OpenRouter spend

- 636 calls, 3,743,228 prompt + 3,483,335 completion tokens, **$2.77** total (`data/cache/deepseek_usage.jsonl`)

## Pairwise difficulty (Bradley-Terry)

- {'pairs_both_orders': 2149, 'order_consistency': 0.8571, 'ties': 14, 'judgments': 4299, 'tasks_with_bt': 2529, 'spearman_bt_vs_teacher': 0.465}
- Pairs are sampled within the primary category (half random, half |Δ teacher diff| ≤ 2). Codex judges each pair in
  both presentation orders in different batches. BT is fitted by penalised gradient ascent (ties = half wins).
- Calibration: per category, a monotone quantile map sends the i-th ranked BT score to the i-th ranked teacher mean
  difficulty of the same tasks (so the marginal matches the teachers, the ordering follows the pairwise judgments).
- Final `labels.difficulty` for BT-scored tasks = 0.5 × teacher soft label + 0.5 × Gaussian(σ=0.6) at the calibrated value.
  Raw values are kept in `meta.difficulty_teacher_mean`, `meta.difficulty_bt.{score,calibrated}`;
  all scores in `data/cache/pairwise/bt_scores.json`.

## Minimal pairs

Edits: add_huge_log 173, add_scope 360, add_screenshots 144, remove_acceptance 136, simplify 264

Fraction where the merged teacher label of the edited task moved as expected vs its original:

| edit: expected delta | ok |
|---|---|
| add_huge_log: checklist.input_gt_50k_tokens | 173/173 (100%) |
| add_huge_log: flags.long_context | 173/173 (100%) |
| add_scope: difficulty | 355/360 (99%) |
| add_screenshots: checklist.has_images | 144/144 (100%) |
| add_screenshots: flags.needs_vision | 144/144 (100%) |
| remove_acceptance: checklist.clear_acceptance_criteria | 81/136 (60%) |
| remove_acceptance: checklist.undefined_terms | 9/10 (90%) |
| remove_acceptance: flags.ambiguous_spec | 89/136 (65%) |
| simplify: checklist.trivial_one_liner | 151/264 (57%) |
| simplify: difficulty | 237/264 (90%) |

## Throughput and teacher calls

| teacher/purpose | calls | ok | mean secs (ok) |
|---|---|---|---|
| codex/generate | 141 | 139 | 155.7 |
| codex/generate-hard | 70 | 70 | 87.5 |
| codex/label | 566 | 560 | 188.2 |
| codex/minimal_pair | 32 | 32 | 126.8 |
| codex/pairwise | 83 | 83 | 97.4 |
| deepseek/label | 573 | 559 | 18.5 |
| deepseek/pairwise | 25 | 25 | 3.9 |
| grok/label | 905 | 211 | 276.7 |
| grok/label_test | 2 | 2 | 299.2 |
| grok/minimal_pair | 26 | 26 | 251.1 |
| kimi/generate | 361 | 10 | 213.6 |
| kimi/label | 32 | 14 | 271.5 |
| kimi/minimal_pair | 1 | 1 | 332.3 |
| ollama/tiebreak | 18 | 18 | 148.7 |

- Total calls 2835, failed 1085, wall clock first→last call 33.12 h
- Batch sizes: generation 20 tasks/call, labelling 15 tasks/call (Ollama 4), pairwise 40 judgments/call, minimal pairs 20 edits/call.

## Label construction

- Soft labels: each teacher's point answer → discretised Gaussian (σ=0.6 levels) for difficulty and every skill axis,
  averaged over teachers; category = mean of teacher distributions (primary 1.0, or 0.75/0.25 with a secondary);
  flags/checklist = mean of 0/1 answers; out_tokens_log10 = mean of log10 estimates.
- Ollama is added as an equal third teacher only where codex and kimi strongly disagree.
- `meta.agreement` = mean over (primary-category match, 1-|Δdiff|/9, 1-mean|Δskill|/10, matching flag+checklist bits) for codex vs kimi.
- Gold exclusion: real records with int(sha1(id),16) % 10 == 0 (instance_id / conversation_hash) are never used.

## Known issues

- **Teacher families and quotas.** The plan was Codex + Kimi. The Kimi CLI hit its 5-hour usage limit (HTTP 429) after
  about 25 successful calls (the quota is shared with other workers). Teacher B then became `grok` (grok-4.7-build-fast
  via `grok -p`, xAI family). Grok then failed with HTTP 402 "usage balance exhausted" after about 3000 tasks. The free
  DeepSeek model via `opencode run` was too slow, so v3 calls DeepSeek V4.1 Flash directly through the OpenRouter API. Only the ~200 pilot tasks carry
  Kimi labels. `meta.teachers` lists each record's teachers. A record with 3 full-label teachers is averaged over all 3.
  Most failed calls in the call log are these fast 429/402 rejections.
- **Single-teacher minimal pairs.** Codex labelled all 1100 minimal pairs, but the second teacher ran out first. The 691
  pairs with only Codex labels are kept (`meta.single_teacher=true`, `meta.agreement=null`), so that the pair margin loss
  has enough data. Filter on `len(meta.teachers) >= 2` to drop them. In data v3 DeepSeek labelled them all, so none are single-teacher any more.
- **Unlabelled pool.** About 4100 pooled tasks (mostly synthetic, plus the rest of the real seeds) have Codex-only labels or
  no labels, and they are excluded. In v3, 404 pool tasks with no labels at all remain excluded; every row in the splits has >= 2 full-label teachers.
- **The Ollama tie-break covers category and difficulty only.** gemma4:26b with `think=false` takes ~15 s per task with
  full labels. That is too slow for full third labels on ~20% of the data, so the tie-break prompt asks only for
  category + difficulty, and those join the soft label for those two fields. Disputed tasks are processed most-disputed
  first. Ollama is shared with the gold worker, and calls slowed to ~300 s per batch, so the tie-break loop was stopped:
  only 167 of the ~14% strongly-disputed records have a third opinion. Resume with `run.py tiebreak`.
- **The `remove_acceptance` and `simplify` checks are weak** (46-63% for the acceptance/ambiguity flags and 57% for
  trivial_one_liner). Teachers often still judge the vague version as having criteria. Rely on `meta.expected_delta`
  for those pairs, not on the teacher labels.
- **The pairwise BT calibration is per category.** BT scores are only comparable within one category. The calibrated
  values follow the teachers' marginal for that category. 1,649 pairs cover 1,847 tasks (~1.8 pairs per task, both orders), so per-task BT
  scores are noisy. That is why the final difficulty mixes 50/50 the teacher soft label and the BT point.
- **Minimal-pair difficulty checks.** The pair checks compare the teacher means of the edited task and its original
  (the BT calibration is applied to originals only). `remove_acceptance` edits sometimes make the task *easier*
  (a smaller scope) rather than only more ambiguous, so use the ambiguity flags, not difficulty, for that edit.
- **Real-seed context.** SWE-rebench/SWE-smith contexts are heuristics: `files_in_scope` comes from the gold patch file
  count, and `estimated_input_tokens` = len(text)/4 + 2500 per file. WildChat contexts hold only an input-token estimate.
  SWE-smith issues are themselves LLM-written (synthetic bugs in real repos), so they are "real" only in repository and
  code. Only 1 of 11 SWE-smith shards was downloaded.
- **WildChat filtering** uses regexes: an English-ish check, a technical/task-like check, and a blocklist for
  role-play/creative/NSFW. Emails, keys, IPs and phone numbers are masked. Some low-quality or odd prompts remain.
- **Embeddings for dedup** are mean-pooled jhu-clsp/ettin-encoder-32m (not a sentence-embedding model), mean-centred to
  remove anisotropy. The 0.95 threshold catches only very close paraphrases. Splits use KMeans clusters (~15 tasks each)
  and one cluster per SWE repo.
- **Generator style.** Synthetic tasks come from Codex (plus a few Kimi batches before the quota ran out). The seed grid
  targets difficulty bands, but labels come only from the teachers, not from the intended band (`meta.cell` keeps the
  target).
- The installed `datasets==2.14.4` is incompatible with `pyarrow==26`, so the raw parquet shards are fetched with
  `huggingface_hub` into `data/raw/hf/`.

## Data v2 changes (2026-10-26)

- **Leak fix**: real SWE rows' `files_in_scope` / `estimated_input_tokens` come from the issue text only (distinct file paths / repo modules named in the text, omitted when none; tokens = len/4 + 4000 fixed repo allowance). Spearman(files_in_scope, multi_file) on SWE rows: train/val/test 0.93 -> 0.08, gold 0.87 -> 0.11.
- **Hard tail**: 700 synthetic tasks (`hrd-*`: 400 hard 7-10, 150 deceptively simple, 150 scary-sounding easy). In v2 they were Codex-only; v3 adds DeepSeek labels.

## Data v3 changes (2026-10-26)

- **DeepSeek V4.1 Flash is the second teacher everywhere** (`deepseek/deepseek-v4.1-flash` via the OpenRouter chat API, reasoning disabled, temperature 0.2, 6-8 calls in parallel, 15 tasks per call, 429/5xx backoff; key read at runtime from the opencode auth store, never written). Usage and cost are logged to `data/cache/deepseek_usage.jsonl`.
- Pilot (30 tasks vs Codex): category accuracy 0.80, difficulty Spearman 0.856. Full run: 8,074 new labels (all pooled Codex-only tasks, the 700 hard tasks, the minimal pairs, every split row) on top of the 300 earlier free-tier ones.
- Merge with 3 teachers is unchanged: difficulty/skill distributions are the mean of the per-teacher Gaussians, category is the mean of one-hots, flags/checklist the mean of bits (the mean of the three points rather than a median keeps disagreement visible in the soft label).
- **Gold**: all 360 candidates have codex + deepseek (79 rows also grok). Ollama (gemma4 no-think) answers stay in `meta.teacher_answers` but no longer enter the soft labels (`gold.EXTRA_TEACHERS`).
- **Pairwise**: 1,000 extra DeepSeek judgements (500 pairs, both orders) in `data/cache/pairwise/judgments_deepseek.jsonl`, joined with the Codex ones for the BT fit.
- Remaining caveat: both main teachers share a prompt, and DeepSeek rates ~0.4 lower than Codex on average (5.37 vs 5.80); the soft label averages the two.
