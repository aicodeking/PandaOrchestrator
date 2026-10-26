# Panda Router training data: statistics

Generated 2026-10-26 05:32 by `scripts/datagen/run.py build`. Format: `schemas/CONTRACTS.md`.

## Totals

- Labelled records: **4895** (originals 3809, minimal pairs 1086)
- Real-seed share of originals: **47.1%** (1793/3809)
- Splits: train 4167, val 364, test 364
- Records with a third (Ollama gemma4:26b) opinion: 167
- Mean per-record agreement (meta.agreement, over full-label teachers): 0.901
- Minimal pairs labelled by a single teacher (meta.single_teacher=true, kept so pairs reach the target): 1391
- Records per full-label teacher set: codex 1381, codex+deepseek 283, codex+grok 3016, codex+grok+deepseek 17, codex+kimi 97, codex+kimi+grok 101
- Near-duplicates dropped (cos > 0.95): 28; clusters: 629; pool tasks not (yet) labelled by enough teachers (excluded): 3841

## Per source

| key | n | % |
|---|---|---|
| synthetic | 2016 | 41.2 |
| minimal-pair | 1086 | 22.2 |
| wildchat | 727 | 14.9 |
| swe-rebench | 657 | 13.4 |
| swe-smith | 409 | 8.4 |

## Per source incl. minimal-pair origin

| key | n | % |
|---|---|---|
| synthetic | 2016 | 41.2 |
| wildchat | 727 | 14.9 |
| swe-rebench | 657 | 13.4 |
| swe-smith | 409 | 8.4 |
| minimal-pair(synthetic) | 381 | 7.8 |
| minimal-pair(wildchat) | 282 | 5.8 |
| minimal-pair(swe-rebench) | 253 | 5.2 |
| minimal-pair(swe-smith) | 170 | 3.5 |

## Per split and source

| split | minimal-pair | swe-rebench | swe-smith | synthetic | wildchat |
|---|---|---|---|---|---|
| train | 930 | 571 | 332 | 1730 | 604 |
| val | 78 | 33 | 57 | 138 | 58 |
| test | 78 | 53 | 20 | 148 | 65 |

## Per primary category (argmax of soft label)

| key | n | % |
|---|---|---|
| bugfix | 1825 | 37.3 |
| implementation | 820 | 16.8 |
| chat_simple | 396 | 8.1 |
| planning | 360 | 7.4 |
| code_review | 264 | 5.4 |
| docs_writing | 250 | 5.1 |
| research | 222 | 4.5 |
| data_analysis | 185 | 3.8 |
| math_reasoning | 170 | 3.5 |
| refactor | 109 | 2.2 |
| test_writing | 106 | 2.2 |
| ui_frontend | 97 | 2.0 |
| devops_infra | 91 | 1.9 |

## Per difficulty (rounded expected difficulty of the final soft label)

| key | n | % |
|---|---|---|
| 6 | 842 | 17.2 |
| 5 | 816 | 16.7 |
| 7 | 782 | 16.0 |
| 4 | 663 | 13.5 |
| 8 | 576 | 11.8 |
| 3 | 477 | 9.7 |
| 2 | 268 | 5.5 |
| 9 | 250 | 5.1 |
| 10 | 160 | 3.3 |
| 1 | 61 | 1.2 |

## Teacher agreement (raw point answers, per teacher pair)

Teachers: codex = gpt-5.6-luna, kimi = Kimi CLI default, grok = grok-4.7-build-fast, ollama = gemma4:26b (tie-break: category + difficulty only).

### codex vs grok

- n = 3134
- Primary category accuracy: **0.8746**
- Difficulty Spearman: **0.8894**, MAE 0.827, means {'codex': 5.44, 'grok': 4.92}
- Strong disagreement (|Δdiff| ≥ 3 or different primary category) rate: 0.1359
- Flag Cohen's κ mean: **0.817**; checklist κ mean: 0.757
- out_tokens (log10) Spearman: 0.9133

| flag | κ |
|---|---|
| needs_tools | 0.948 |
| needs_vision | 0.939 |
| long_context | 1.0 |
| needs_review | 0.708 |
| ambiguous_spec | 0.53 |
| multi_file | 0.874 |
| needs_web | 0.72 |

| checklist id | κ |
|---|---|
| edits_code | 0.904 |
| touches_gt3_files | 0.576 |
| new_feature | 0.812 |
| has_failing_behavior | 0.925 |
| needs_root_cause | 0.755 |
| needs_run_commands | 0.942 |
| needs_browser_or_web | 0.698 |
| has_images | 0.965 |
| input_gt_50k_tokens | 1.0 |
| concurrency_or_distributed | 0.861 |
| security_sensitive | 0.883 |
| formal_math_or_proof | 0.716 |
| domain_expertise | 0.442 |
| clear_acceptance_criteria | 0.631 |
| undefined_terms | 0.435 |
| design_decisions | 0.662 |
| visual_ui_work | 0.846 |
| writes_prose | 0.857 |
| data_processing | 0.763 |
| infra_config | 0.811 |
| multi_step_plan | 0.641 |
| reviews_existing_work | 0.64 |
| trivial_one_liner | 0.635 |
| high_stakes | 0.76 |

| skill axis | Spearman |
|---|---|
| coding | 0.865 |
| debugging | 0.926 |
| reasoning | 0.879 |
| math | 0.765 |
| writing | 0.868 |
| research | 0.679 |
| review | 0.733 |
| planning | 0.866 |
| ui_frontend | 0.877 |
| data_analysis | 0.804 |

### codex vs kimi

- n = 198
- Primary category accuracy: **0.8283**
- Difficulty Spearman: **0.9151**, MAE 1.247, means {'codex': 6.03, 'kimi': 4.84}
- Strong disagreement (|Δdiff| ≥ 3 or different primary category) rate: 0.197
- Flag Cohen's κ mean: **0.704**; checklist κ mean: 0.693
- out_tokens (log10) Spearman: 0.9139

| flag | κ |
|---|---|
| needs_tools | 0.919 |
| needs_vision | 1.0 |
| long_context | 1.0 |
| needs_review | 0.546 |
| ambiguous_spec | 0.141 |
| multi_file | 0.525 |
| needs_web | 0.799 |

| checklist id | κ |
|---|---|
| edits_code | 0.827 |
| touches_gt3_files | 0.518 |
| new_feature | 0.778 |
| has_failing_behavior | 0.939 |
| needs_root_cause | 0.739 |
| needs_run_commands | 0.919 |
| needs_browser_or_web | 0.75 |
| has_images | 0.969 |
| input_gt_50k_tokens | 1.0 |
| concurrency_or_distributed | 0.722 |
| security_sensitive | 0.821 |
| formal_math_or_proof | 0.644 |
| domain_expertise | 0.5 |
| clear_acceptance_criteria | 0.614 |
| undefined_terms | 0.165 |
| design_decisions | 0.491 |
| visual_ui_work | 0.858 |
| writes_prose | 0.734 |
| data_processing | 0.588 |
| infra_config | 0.798 |
| multi_step_plan | 0.453 |
| reviews_existing_work | 0.576 |
| trivial_one_liner | 0.552 |
| high_stakes | 0.68 |

| skill axis | Spearman |
|---|---|
| coding | 0.831 |
| debugging | 0.902 |
| reasoning | 0.885 |
| math | 0.746 |
| writing | 0.852 |
| research | 0.739 |
| review | 0.739 |
| planning | 0.868 |
| ui_frontend | 0.861 |
| data_analysis | 0.752 |

### kimi vs grok

- n = 101
- Primary category accuracy: **0.8713**
- Difficulty Spearman: **0.9256**, MAE 0.713, means {'kimi': 4.91, 'grok': 5.54}
- Strong disagreement (|Δdiff| ≥ 3 or different primary category) rate: 0.1287
- Flag Cohen's κ mean: **0.738**; checklist κ mean: 0.736
- out_tokens (log10) Spearman: 0.9537

| flag | κ |
|---|---|
| needs_tools | 0.98 |
| needs_vision | 1.0 |
| long_context | 1.0 |
| needs_review | 0.612 |
| ambiguous_spec | 0.287 |
| multi_file | 0.424 |
| needs_web | 0.864 |

| checklist id | κ |
|---|---|
| edits_code | 0.881 |
| touches_gt3_files | 0.593 |
| new_feature | 0.799 |
| has_failing_behavior | 0.901 |
| needs_root_cause | 0.64 |
| needs_run_commands | 0.98 |
| needs_browser_or_web | 0.864 |
| has_images | 1.0 |
| input_gt_50k_tokens | 1.0 |
| concurrency_or_distributed | 0.806 |
| security_sensitive | 0.879 |
| formal_math_or_proof | 0.521 |
| domain_expertise | 0.705 |
| clear_acceptance_criteria | 0.585 |
| undefined_terms | 0.266 |
| design_decisions | 0.613 |
| visual_ui_work | 0.864 |
| writes_prose | 0.735 |
| data_processing | 0.775 |
| infra_config | 0.742 |
| multi_step_plan | 0.563 |
| reviews_existing_work | 0.668 |
| trivial_one_liner | 0.595 |
| high_stakes | 0.684 |

| skill axis | Spearman |
|---|---|
| coding | 0.864 |
| debugging | 0.912 |
| reasoning | 0.929 |
| math | 0.798 |
| writing | 0.907 |
| research | 0.652 |
| review | 0.773 |
| planning | 0.893 |
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
| codex/generate-hard | 70 | 70 | 87.5 |
| codex/label | 566 | 560 | 188.2 |
| codex/minimal_pair | 32 | 32 | 126.8 |
| codex/pairwise | 83 | 83 | 97.4 |
| deepseek/label | 34 | 20 | 139.2 |
| grok/label | 905 | 211 | 276.7 |
| grok/label_test | 2 | 2 | 299.2 |
| grok/minimal_pair | 26 | 26 | 251.1 |
| kimi/generate | 361 | 10 | 213.6 |
| kimi/label | 32 | 14 | 271.5 |
| kimi/minimal_pair | 1 | 1 | 332.3 |
| ollama/tiebreak | 18 | 18 | 148.7 |

- Total calls 2271, failed 1085, wall clock first→last call 24.23 h
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

## Data v2 changes (2026-10-26)

- **Leak fix**: real SWE rows' `files_in_scope` / `estimated_input_tokens` now come from the issue text only (distinct file paths / repo modules named in the text, omitted when none; tokens = len/4 + 4000 fixed repo allowance). Spearman(files_in_scope, multi_file) on SWE rows: train/val/test 0.93 -> 0.08 (222/1066 rows name a file), gold 0.87 -> 0.11.
- **Hard tail**: 700 synthetic tasks (`hrd-*`: 400 hard 7-10, 150 deceptively simple, 150 scary-sounding easy), labelled by Codex only (single_teacher=true) because no second teacher was available (Grok 402 balance exhausted, Kimi 5h limit, opencode free DeepSeek limit hit after 315 labels).
- DeepSeek (opencode free) added 315 second labels before its limit; the ~3,840 remaining pool tasks stay excluded (Codex labels cached for when a 2nd teacher returns).

| difficulty | v1 n | v1 % | v2 n | v2 % |
|---|---|---|---|---|
| 1 | 58 | 1.5 | 61 | 1.2 |
| 2 | 248 | 6.4 | 268 | 5.5 |
| 3 | 442 | 11.4 | 477 | 9.7 |
| 4 | 604 | 15.5 | 663 | 13.5 |
| 5 | 728 | 18.7 | 816 | 16.7 |
| 6 | 749 | 19.2 | 842 | 17.2 |
| 7 | 636 | 16.3 | 782 | 16.0 |
| 8 | 355 | 9.1 | 576 | 11.8 |
| 9 | 63 | 1.6 | 250 | 5.1 |
| 10 | 10 | 0.3 | 160 | 3.3 |

Share of difficulty 7-10: v1 27.3% -> v2 36.1%.

Codex vs DeepSeek (n=300): category agree 0.837, difficulty Spearman 0.887, mean diff codex 6.63 vs deepseek 6.15.
