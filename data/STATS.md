# Panda Router training data: statistics

Generated 2026-10-25 08:29 by `scripts/datagen/run.py build`. Format: `schemas/CONTRACTS.md`.

## Totals

- Labelled records: **3893** (originals 2807, minimal pairs 1086)
- Real-seed share of originals: **63.4%** (1779/2807)
- Splits: train 3314, val 279, test 300
- Records with a third (Ollama gemma4:26b) opinion: 167
- Mean per-record agreement (meta.agreement, over full-label teachers): 0.902
- Minimal pairs labelled by a single teacher (meta.single_teacher=true, kept so pairs reach the target): 691
- Records per full-label teacher set: codex 682, codex+grok 3014, codex+kimi 97, codex+kimi+grok 100
- Near-duplicates dropped (cos > 0.95): 27; clusters: 563; pool tasks not (yet) labelled by enough teachers (excluded): 4144

## Per source

| key | n | % |
|---|---|---|
| minimal-pair | 1086 | 27.9 |
| synthetic | 1028 | 26.4 |
| wildchat | 721 | 18.5 |
| swe-rebench | 653 | 16.8 |
| swe-smith | 405 | 10.4 |

## Per source incl. minimal-pair origin

| key | n | % |
|---|---|---|
| synthetic | 1028 | 26.4 |
| wildchat | 721 | 18.5 |
| swe-rebench | 653 | 16.8 |
| swe-smith | 405 | 10.4 |
| minimal-pair(synthetic) | 381 | 9.8 |
| minimal-pair(wildchat) | 282 | 7.2 |
| minimal-pair(swe-rebench) | 253 | 6.5 |
| minimal-pair(swe-smith) | 170 | 4.4 |

## Per split and source

| split | minimal-pair | swe-rebench | swe-smith | synthetic | wildchat |
|---|---|---|---|---|---|
| train | 929 | 544 | 302 | 924 | 615 |
| val | 68 | 56 | 96 | 36 | 23 |
| test | 89 | 53 | 7 | 68 | 83 |

## Per primary category (argmax of soft label)

| key | n | % |
|---|---|---|
| bugfix | 1540 | 39.6 |
| implementation | 619 | 15.9 |
| chat_simple | 391 | 10.0 |
| planning | 253 | 6.5 |
| docs_writing | 206 | 5.3 |
| research | 185 | 4.8 |
| code_review | 170 | 4.4 |
| data_analysis | 149 | 3.8 |
| ui_frontend | 87 | 2.2 |
| test_writing | 82 | 2.1 |
| refactor | 81 | 2.1 |
| math_reasoning | 69 | 1.8 |
| devops_infra | 61 | 1.6 |

## Per difficulty (rounded expected difficulty of the final soft label)

| key | n | % |
|---|---|---|
| 6 | 749 | 19.2 |
| 5 | 728 | 18.7 |
| 7 | 636 | 16.3 |
| 4 | 604 | 15.5 |
| 3 | 442 | 11.4 |
| 8 | 355 | 9.1 |
| 2 | 248 | 6.4 |
| 9 | 63 | 1.6 |
| 1 | 58 | 1.5 |
| 10 | 10 | 0.3 |

## Teacher agreement (raw point answers, per teacher pair)

Teachers: codex = gpt-5.6-luna, kimi = Kimi CLI default, grok = grok-4.7-build-fast, ollama = gemma4:26b (tie-break: category + difficulty only).

### codex vs grok

- n = 3114
- Primary category accuracy: **0.8738**
- Difficulty Spearman: **0.8892**, MAE 0.827, means {'codex': 5.45, 'grok': 4.92}
- Strong disagreement (|Δdiff| ≥ 3 or different primary category) rate: 0.1368
- Flag Cohen's κ mean: **0.818**; checklist κ mean: 0.757
- out_tokens (log10) Spearman: 0.9135

| flag | κ |
|---|---|
| needs_tools | 0.948 |
| needs_vision | 0.939 |
| long_context | 1.0 |
| needs_review | 0.708 |
| ambiguous_spec | 0.532 |
| multi_file | 0.876 |
| needs_web | 0.724 |

| checklist id | κ |
|---|---|
| edits_code | 0.905 |
| touches_gt3_files | 0.576 |
| new_feature | 0.812 |
| has_failing_behavior | 0.925 |
| needs_root_cause | 0.753 |
| needs_run_commands | 0.942 |
| needs_browser_or_web | 0.701 |
| has_images | 0.965 |
| input_gt_50k_tokens | 1.0 |
| concurrency_or_distributed | 0.86 |
| security_sensitive | 0.882 |
| formal_math_or_proof | 0.716 |
| domain_expertise | 0.443 |
| clear_acceptance_criteria | 0.634 |
| undefined_terms | 0.436 |
| design_decisions | 0.661 |
| visual_ui_work | 0.846 |
| writes_prose | 0.857 |
| data_processing | 0.764 |
| infra_config | 0.812 |
| multi_step_plan | 0.642 |
| reviews_existing_work | 0.638 |
| trivial_one_liner | 0.633 |
| high_stakes | 0.759 |

| skill axis | Spearman |
|---|---|
| coding | 0.865 |
| debugging | 0.926 |
| reasoning | 0.879 |
| math | 0.766 |
| writing | 0.868 |
| research | 0.679 |
| review | 0.732 |
| planning | 0.865 |
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

## Pairwise difficulty (Bradley-Terry)

- {'pairs_both_orders': 1649, 'order_consistency': 0.8775, 'ties': 9, 'judgments': 3299, 'tasks_with_bt': 1847, 'spearman_bt_vs_teacher': 0.4903}
- Pairs are sampled within the primary category (half random, half |Δ teacher diff| ≤ 2). Codex judges each pair in
  both presentation orders in different batches. BT is fitted by penalised gradient ascent (ties = half wins).
- Calibration: per category, a monotone quantile map sends the i-th ranked BT score to the i-th ranked teacher mean
  difficulty of the same tasks (so the marginal matches the teachers, the ordering follows the pairwise judgments).
- Final `labels.difficulty` for BT-scored tasks = 0.5 × teacher soft label + 0.5 × Gaussian(σ=0.6) at the calibrated value.
  Raw values are kept in `meta.difficulty_teacher_mean`, `meta.difficulty_bt.{score,calibrated}`;
  all scores in `data/cache/pairwise/bt_scores.json`.

## Minimal pairs

Edits: add_huge_log 174, add_scope 362, add_screenshots 144, remove_acceptance 138, simplify 268

Fraction where the merged teacher label of the edited task moved as expected vs its original:

| edit: expected delta | ok |
|---|---|
| add_huge_log: checklist.input_gt_50k_tokens | 173/174 (99%) |
| add_huge_log: flags.long_context | 173/174 (99%) |
| add_scope: difficulty | 357/362 (99%) |
| add_screenshots: checklist.has_images | 144/144 (100%) |
| add_screenshots: flags.needs_vision | 144/144 (100%) |
| remove_acceptance: checklist.clear_acceptance_criteria | 64/138 (46%) |
| remove_acceptance: checklist.undefined_terms | 7/10 (70%) |
| remove_acceptance: flags.ambiguous_spec | 87/138 (63%) |
| simplify: checklist.trivial_one_liner | 154/268 (57%) |
| simplify: difficulty | 239/268 (89%) |

## Throughput and teacher calls

| teacher/purpose | calls | ok | mean secs (ok) |
|---|---|---|---|
| codex/generate | 141 | 139 | 155.7 |
| codex/label | 305 | 303 | 188.7 |
| codex/minimal_pair | 32 | 32 | 126.8 |
| codex/pairwise | 83 | 83 | 97.4 |
| deepseek/label | 1 | 0 | 0.0 |
| grok/label | 905 | 211 | 276.7 |
| grok/label_test | 2 | 2 | 299.2 |
| grok/minimal_pair | 26 | 26 | 251.1 |
| kimi/generate | 361 | 10 | 213.6 |
| kimi/label | 32 | 14 | 271.5 |
| kimi/minimal_pair | 1 | 1 | 332.3 |
| ollama/tiebreak | 18 | 18 | 148.7 |

- Total calls 1907, failed 1068, wall clock first→last call 3.15 h
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
  via `grok -p`, xAI family). Grok then failed with HTTP 402 "usage balance exhausted" after about 3000 tasks. A free
  DeepSeek model via `opencode run` timed out (20 min for one batch), so it was not used. Only the ~200 pilot tasks carry
  Kimi labels. `meta.teachers` lists each record's teachers. A record with 3 full-label teachers is averaged over all 3.
  Most failed calls in the call log are these fast 429/402 rejections.
- **Single-teacher minimal pairs.** Codex labelled all 1100 minimal pairs, but the second teacher ran out first. The 691
  pairs with only Codex labels are kept (`meta.single_teacher=true`, `meta.agreement=null`), so that the pair margin loss
  has enough data. Filter on `len(meta.teachers) >= 2` to drop them. Every original has >= 2 teachers.
- **Unlabelled pool.** About 4100 pooled tasks (mostly synthetic, plus the rest of the real seeds) have Codex-only labels or
  no labels, and they are excluded. Resume with `run.py label --teachers kimi` (or `grok`) once a quota resets, then `build`.
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
