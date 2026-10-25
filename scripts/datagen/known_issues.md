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
