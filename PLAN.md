# Panda Router: a small local decision model for picking which model gets a task

## 1. What we're building

A **System One decision model**, in the same spirit as Jev (TypeSafe AI). It doesn't generate text.
The main orchestrator sends it a **task** and a **model pool** (JSON model cards). It returns **typed
answers with calibrated probabilities**:

- **Choice**: which model, plus a probability for every candidate.
- **Score**: difficulty on an ordinal 1–10 scale.
- **Flags**: yes/no probabilities such as `needs_tools`, `needs_vision`, `long_context`, `needs_review`.

Ordinary, testable code then turns those answers into a decision: hard filters, a utility function,
a confidence floor and a fallback. The model supplies the judgment. Policy stays in code.

### Design rules

1. **The pool is data, not weights.** Models are described by their cards. The router must handle
   a model it has never seen, using only the card, so a new model is a JSON change and needs no
   retraining.
2. **Every output is inside the schema.** The router can't return a model that isn't in the pool.
3. **Probabilities are calibrated.** P(success)=0.8 should be correct about 80% of the time,
   because the orchestrator automates on these numbers.
4. **Tiny and local.** Target size is 25–150 MB on disk (int8 ONNX), with p50 latency under 20 ms
   on a laptop CPU and no GPU needed.

## 2. Architecture

```
            ┌────────────────────┐
 task ────▶ │ Task encoder       │──▶ t (d=384/768) ──┬──▶ task heads: category, difficulty, flags
            │ (small BERT-class) │                    │
            └────────────────────┘                    ▼
                                         ┌──────────────────────────┐
 model card ─▶ Card encoder ─▶ m_i  ───▶ │ Interaction head (MLP)   │──▶ per-model: p_success_i,
 (text + numeric                         │ [t, m_i, t⊙m_i, num_i]   │    quality_i, est_out_tokens_i
  features, cached)                      └──────────────────────────┘
                                                      │
                                                      ▼
                        Deterministic policy (code): filter → utility → floor/fallback → ranked list
```

- **Task encoder**: a small encoder-only transformer from the **Ettin** family
  (`jhu-clsp/ettin-encoder-*`, sizes 17M/32M/68M/150M/400M/1B). These use the ModernBERT
  architecture with 8k context, were trained on open data that includes code, and beat ModernBERT
  at matched size. Every size shares one tokenizer, so we can distil a big one into a small one
  directly. Three roles:
  - **Teacher**: `ettin-encoder-400m`, or `ettin-encoder-1b` if the data supports it.
    Used offline only.
  - **Default ship**: `ettin-encoder-150m`, about 150 MB int8.
  - **Tiny ship**: `ettin-encoder-32m` or `ettin-encoder-68m`, distilled from the teacher, about
    35–70 MB int8.
  - Benchmarked against them in Phase 3: ModernBERT-base, plus `Qwen3-Reranker-0.6B` as a
    cross-encoder (task+card → score, 32k context, strong on code), plus `katanemo/Arch-Router-1.5B`
    as a zero-shot generative routing baseline.
  - **Licences**, checked 2026-10-25:
    - Ettin (all sizes): **MIT**.
    - ModernBERT and Qwen3-Reranker: **Apache-2.0**.
    - Arch-Router: **Katanemo Community License**. Commercial use needs a separate licence from
      DigitalOcean. Any model trained on its outputs must carry a "DigitalOcean" name prefix. So
      use it **only as a private benchmark, never to make labels**.
    - LFM2.5-Encoder: **LFM Open License v1.0**. Commercial use is not licensed for entities with
      $10M or more in annual revenue.
  - Input: the task text, plus a compact context string (repo language, file count, whether
    attachments or images are present).
- **Card encoder**: the same backbone, run on the card's `description` and `strengths` text, joined
  with an MLP over the numeric fields (capability scores, price, context window, latency, tool and
  vision support). Card embeddings are computed **once per pool** and cached, so routing costs one
  forward pass of the task encoder plus N small MLP calls.
- **Optional ID residual**: known models get a small learned embedding added to `m_i`. During
  training we drop it out about 50% of the time, so the router never depends on it and can fall
  back to the card for unseen models.
- **Why not a small generative LLM, for example a 0.5B model emitting JSON?** It's slower,
  its confidences are uncalibrated, it can name models outside the pool, and it is harder to train
  on outcome data. A scoring architecture fixes all four problems.

## 3. Schemas

### 3.1 Model card: `ModelCard` (supplied by the orchestrator, one per candidate)

```jsonc
{
  "id": "claude-sonnet",                       // stable key the orchestrator dispatches on
  "provider": "claude",                        // harness / API family
  "model": "sonnet",
  "description": "Strong all-round coder, good at multi-file edits and tool use.",
  "strengths": ["multi_file_refactor", "tool_use", "code_review"],
  "weaknesses": ["very_long_context_recall"],
  "capabilities": {                            // 0..1, fixed taxonomy (see 3.4); missing = unknown
    "coding": 0.88, "debugging": 0.85, "reasoning": 0.80, "math": 0.70,
    "writing": 0.82, "research": 0.70, "review": 0.86, "planning": 0.78,
    "ui_frontend": 0.80, "data_analysis": 0.72
  },
  "modalities": { "input": ["text", "image"], "output": ["text"] },
  "features": { "tools": true, "json_mode": true, "reasoning_effort": ["low", "medium", "high"] },
  "limits": { "context_tokens": 200000, "max_output_tokens": 64000 },
  "cost": { "input_per_mtok": 3.0, "output_per_mtok": 15.0, "currency": "USD" },
  "latency": { "ttft_ms_p50": 900, "tokens_per_sec": 80 },
  "local": false,
  "tags": ["harness:claude-code"],
  "card_version": "2026-10-01"
}
```

Required fields: `id`, `description`, `limits.context_tokens`, `cost`. Every other field is
optional, and the router treats a missing field as unknown. This works because training randomly
masks card fields.

### 3.2 Request: `RouteRequest` (orchestrator → router)

```jsonc
{
  "task": {
    "text": "Refactor the auth middleware to support JWT rotation and add tests.",
    "kind_hint": "implementation",              // optional, from orchestrator
    "context": {
      "repo_languages": ["typescript"], "files_in_scope": 6,
      "estimated_input_tokens": 18000, "has_images": false, "requires_tools": true
    }
  },
  "pool": ["claude-sonnet", "claude-haiku", "codex-gpt-6-luna", "glm-glm-5-1"],  // ids, or inline ModelCard[]
  "constraints": {
    "max_cost_usd": 0.50, "max_latency_ms": null, "local_only": false,
    "require": ["tools"], "exclude": []
  },
  "preferences": {
    "mode": "cheapest_above_threshold",         // or "max_utility" | "max_quality"
    "min_p_success": 0.75,
    "weights": { "quality": 1.0, "cost": 0.3, "latency": 0.1 }
  },
  "questions": ["choice", "difficulty", "flags"],  // ask only what you need
  "return_top_k": 3
}
```

### 3.3 Response: `RouteResponse` (router → orchestrator)

```jsonc
{
  "choice": {
    "model_id": "claude-sonnet",
    "confidence": 0.81,                         // calibrated P(success) of the chosen model
    "decided_by": "policy:cheapest_above_threshold"
  },
  "ranking": [                                  // top_k, all inside the pool
    { "model_id": "claude-sonnet",    "p_success": 0.81, "quality": 0.78, "est_cost_usd": 0.21, "est_latency_ms": 41000 },
    { "model_id": "codex-gpt-6-luna", "p_success": 0.77, "quality": 0.74, "est_cost_usd": 0.09, "est_latency_ms": 35000 },
    { "model_id": "claude-haiku",     "p_success": 0.52, "quality": 0.55, "est_cost_usd": 0.03, "est_latency_ms": 12000 }
  ],
  "filtered_out": [ { "model_id": "glm-glm-5-1", "reason": "constraint:require=tools" } ],
  "difficulty": { "level": 6, "distribution": [0,0,.02,.05,.13,.38,.27,.11,.03,.01] },
  "category":   { "label": "implementation", "p": 0.91 },
  "flags": { "needs_tools": 0.97, "needs_vision": 0.01, "long_context": 0.08, "needs_review": 0.64 },
  "fallback": { "triggered": false, "floor": 0.55, "default_model": "claude-opus" },
  "router": { "version": "panda-router-0.3.0-int8", "latency_ms": 11, "pool_hash": "9f2c…" },
  "trace_id": "r_01J…"                          // join key for outcome feedback
}
```

### 3.4 Fixed taxonomies (version them)

- **Category** (`task.kind`): `implementation`, `bugfix`, `refactor`, `test_writing`,
  `code_review`, `research`, `planning`, `docs_writing`, `ui_frontend`, `data_analysis`, `math`,
  `chat_simple`, `other`.
- **Capability axes**: the same list as `capabilities` above. These axes are the bridge between
  tasks and cards.
- **Flags**: `needs_tools`, `needs_vision`, `long_context`, `needs_review`, `ambiguous_spec`.

### 3.5 Feedback: `RouteOutcome` (orchestrator → router log, after the worker finishes)

```jsonc
{
  "trace_id": "r_01J…", "model_id": "claude-sonnet",
  "propensity": 0.81,                          // probability the policy picked this model (needed for off-policy learning)
  "success": true,                             // tests pass / reviewer accepted / user didn't override
  "signals": { "tests_passed": true, "review_verdict": "approve", "retries": 0, "user_override": null },
  "quality": 0.85,                             // optional judge score 0..1
  "actual_cost_usd": 0.18, "actual_latency_ms": 38000, "tokens": { "in": 21000, "out": 4200 }
}
```

## 4. The decision policy (code, not weights)

1. **Hard filter**: drop models that miss `require`, violate `local_only` or `exclude`, have too
   small a context (`estimated_input_tokens` × 1.2 > `context_tokens`), lack a needed modality
   (`needs_vision` > 0.5), or have an estimated cost above `max_cost_usd`.
2. **Score**: `est_cost = price · (in_tokens + est_out_tokens_i)`. The utility is
   `U_i = w_q·quality_i·p_success_i − w_c·norm(est_cost_i) − w_l·norm(est_latency_i)`.
3. **Mode**:
   - `cheapest_above_threshold`: the cheapest model with `p_success ≥ min_p_success`.
   - `max_utility`: argmax U.
   - `max_quality`: argmax `p_success`.
4. **Floor**: if no candidate clears the floor, use `default_model` and set `fallback.triggered`.
5. **Escalation ladder**: the `ranking` doubles as a cascade. If the orchestrator's first pick
   fails, it tries the next model by `p_success` and logs both outcomes.
6. **Exploration (online only)**: with small ε, or with Thompson sampling, pick a non-argmax
   candidate that is still above the floor. Always log the propensity.

## 5. Training

### 5.1 What each training example is

`(task, context, card_i, masked/perturbed) → {success_i, quality_i, out_tokens_i}`, plus task-level
labels `{category, difficulty, flags}`. A single task with outcomes for K models gives K pointwise
examples and K(K−1)/2 pairwise examples.

### 5.2 Data sources, in build order

| # | Source | Gives | Notes |
|---|--------|-------|-------|
| A | **Teacher labelling** | category, difficulty, flags for 200k–1M prompts | A strong LLM labels diverse prompts: public instruction and coding datasets plus synthetic orchestration tasks. Cheap, and it bootstraps the task heads. |
| B | **Public routing and benchmark data** | success matrices across many models | Candidates to verify licence and format: RouterBench, the RouteLLM / Chatbot Arena preference data, per-sample results from open leaderboards (HELM, Open LLM Leaderboard details), SWE-bench-style per-instance results. Good for generic "can model X do task Y". |
| C | **Our own eval harness** (most important) | task × model outcome matrix on *our* task distribution | Build 2–5k orchestration tasks with automatic graders: unit tests, linters/typecheck, diff applies, and a pairwise LLM-judge panel. Run every roster model through PandaCode's real harnesses (claude, codex, kimi, glm, grok, devin…). Log success, quality, cost, latency and tokens. |
| D | **Production logs** | `RouteOutcome` from real orchestration | Only the chosen model's outcome is observed, so learn with propensity weighting (IPS / doubly-robust). Escalation-ladder failures give free "A failed, B succeeded" pairs. |
| E | **Card generation** | capability scores for cards | Fill the numeric `capabilities` from C (per-category success rates), so cards are grounded in evidence instead of marketing. |

### 5.3 Losses (multi-task)

- `p_success`: binary cross-entropy (BCE), IPS-weighted for D.
- Pairwise ranking: Bradley–Terry / logistic on `s_i − s_j` for preference data from B and judge
  pairs from C.
- `quality`: MSE or Huber loss, when a score exists.
- `est_out_tokens`: Huber loss on log(tokens). This feeds cost estimation.
- `difficulty`: ordinal loss (CORAL / cumulative logits), not plain softmax.
- `category`: cross-entropy (CE). `flags`: BCE.
- Total: a weighted sum. Tune the weights on the validation routing metric, not on the loss.

### 5.4 Augmentations that make it generalise to new models

- **Card dropout**: randomly mask 0–60% of card fields and drop `strengths` text.
- **Name scrubbing**: replace model names and IDs with random tokens, so the router reads the
  capabilities instead of memorising brands.
- **Price and latency jitter**: about ±30%, so the router learns that cost matters relatively.
- **Pool sampling**: train on random pools of 2–12 models, with shuffled order.
- **Leave-models-out**: hold out entire model families for zero-shot evaluation.

### 5.5 Training recipe

1. **Stage 1, task heads**: fine-tune the encoder on data A (category, difficulty, flags). This
   takes a few GPU-hours on one consumer GPU, or works on Apple Silicon via PyTorch MPS.
2. **Stage 2, router**: add the card encoder and the interaction head, then train on B+C with all
   losses. Freeze the lower encoder layers at first, then unfreeze.
3. **Stage 3, calibrate**: apply temperature scaling, or isotonic regression per head, on a
   held-out split of C. Report expected calibration error (ECE).
4. **Stage 4, distil and shrink (optional)**: distil the default-tier model into the tiny tier,
   using logits from the teacher router. Export to ONNX and apply int8 dynamic quantisation.
5. **Stage 5, continuous**: retrain weekly on C plus IPS-weighted D. Ship a new version only if it
   wins offline replay (§6).

## 6. Evaluation: how we know it's better

| Metric | Meaning | Target v1 |
|---|---|---|
| **Quality–cost AUC** | Sweep the cost weight and plot success rate against $ spent (RouterBench-style). | Beats "always best model" on cost at ≥95% of its success rate |
| **Oracle gap** | Our success at equal cost vs. a hindsight-perfect router. | Close ≥50% of the gap between random and oracle |
| **Top-1 / top-3 agreement** with the oracle's cheapest successful model | | Report |
| **ECE** of `p_success` | Calibration. | < 0.05 |
| **Zero-shot** metrics on held-out models | Card generalisation. | ≤10% worse than in-distribution |
| **Latency** p50/p95 on CPU, pool=12 | | < 20 ms / < 50 ms |
| **Offline replay (IPS/DR)** on production logs | Estimates a new version's value before shipping. | Must beat the current version |

Baselines to beat: always the strongest model; always the cheapest model; a heuristic based on
`kind_hint` and length; an embedding kNN; a large LLM asked "which model?".

## 7. How it gets better over time (the flywheel)

1. Every route logs `RouteRequest`, `RouteResponse`, the propensity and the eventual `RouteOutcome`.
2. ε-exploration and escalation ladders produce counterfactual signal at low cost.
3. Nightly, recompute per-model capability scores from outcomes and update the cards. This
   improves routing **without retraining**.
4. Weekly, retrain on fresh data, calibrate, replay-evaluate, then ship or reject.
5. When a new model is added to the roster, write its card and run it on a **200-task probe set**
   from C to fill its `capabilities`. It is routable immediately, through zero-shot use of the card.
6. Drift monitors watch for a falling success rate per model or category, rising fallback rate, or
   calibration drift. Any of these triggers a re-probe.

## 8. Serving locally

- Artefacts: `router.onnx` (int8), `tokenizer.json`, `taxonomy.json`, `policy.yaml`.
- Runtime: ONNX Runtime on CPU, exposed as a tiny local HTTP/stdio service
  (`POST /route`, `POST /outcome`). An MCP tool wrapper lets any orchestrator agent call it directly.
- Card embeddings are cached by `pool_hash`. Outcome logs go to local SQLite or JSONL.
- Fallback: if the router process is down, the orchestrator uses the deterministic heuristic
  baseline.

## 9. Proposed repo layout

```
schemas/        model_card.schema.json, route_request/response/outcome.schema.json, taxonomy.json
cards/          one JSON card per roster model
router/         model.py (encoders + heads), policy.py, losses.py, calibrate.py, export_onnx.py
data/           builders for A–E, augmentation, splits (leave-models-out)
harness/        eval task suite + graders + runners that call PandaCode harnesses
serve/          ONNX runtime server + MCP tool + SQLite logger
eval/           routing metrics, replay (IPS/DR), dashboards
```

## 10. Phased plan

| Phase | Deliverable | Exit criteria |
|---|---|---|
| **0. Spec** | JSON Schemas, taxonomy v1, cards for the current roster | Schemas validate; orchestrator can build a `RouteRequest` |
| **1. Heuristic router + logging** | `serve/` with the policy plus a rule-based scorer, outcome logging | Orchestrator routes through it end to end; logs are flowing |
| **2. Eval harness** | 2–5k graded tasks, runners for every roster model | Full task × model outcome matrix with cost and latency |
| **3. Router v1** | Two-tower model trained on A+B+C, calibrated, int8 ONNX | Beats all baselines on quality–cost AUC; ECE < 0.05; p50 < 20 ms |
| **4. Tiny tier** | Distilled ~25 MB model | ≤3% AUC loss vs. default tier |
| **5. Online loop** | Exploration, IPS retraining, replay gate, card auto-refresh | A shipped version wins replay over the previous one |

## 11. Open decisions

1. **Success definition per category**: tests pass, reviewer approval or judge score ≥ τ. This
   choice drives every label.
2. **Routing scope**: model only, or model + reasoning effort + harness? Effort could be expanded
   into separate "virtual cards", for example `claude-opus@high`.
3. **Budget for Phase 2 eval runs**: running every roster model on thousands of tasks is the
   main cost.
4. **Public data licences**: verify per dataset before any use beyond research.
5. **Single task or multi-step**: should the router also decide decomposition, or only "who
   does this assignment"? v1 recommends only "who".

---

## 12. v1 design: synthetic-first task profiler + card matcher (research-backed)

For v1 this section **replaces §2 and §5**. The two-tower learned matcher becomes an optional v2,
to build only once real outcome logs exist.

### 12.1 Split of responsibilities

```
task ──▶ Ettin task profiler (trained) ──▶ profile: category, difficulty dist (1–10), per-axis skill-level dists,
                                                    flags, log(out_tokens) quantiles, ~30 checklist answers
model cards (θ_axis ± SE, price, limits) ─┐
                                          └──▶ matcher (code): filter → P(success) → utility → pick + ranking
```

**P(success)** uses compensatory multidimensional item response theory (MIRT) with one
discrimination value per model. For a task with axis weights w (from the profile) and difficulty
b, the success probability for model i is:

```
P_i = sigmoid( a_i · ( Σ_k w_k·θ_i,k − b ) )
```

This is **integrated over** the profiler's ordinal distribution for b and over the card's
standard error on θ, instead of using point estimates. That integration is what makes the output
probabilities honest. **Expected cost to success** is
`(in_tokens + E[out_tokens]) · price / P_i`, and it is used in `cheapest_above_threshold`.

### 12.2 Data: synthetic, but anchored to reality

| Step | What | Why / source |
|---|---|---|
| 1. Seed grid | Enumerate category × axis × difficulty band × stack × flags, then fill every cell. | Even coverage and balanced ordinal bins (GLAN, arXiv:2402.13064) |
| 2. Real seeds (≥30%) | Real tasks rewritten by the teacher. | Prevents shortcut learning on the generator's style. See the licence list after this table. |
| 3. Persona rewrites | Self-made personas, e.g. vague PM, terse SRE, junior dev. | Varies the writing style (Persona Hub idea, arXiv:2406.20094). Its released data is CC-BY-NC-SA, so we make our own personas. |
| 4. Checklist labelling | The teacher answers about 30 atomic yes/no questions, e.g. "touches >3 files?", "needs browser?", "undefined term in spec?". Code maps the answers to flags and skill seeds. | Binary questions agree far better than 1–10 scores (BenchBuilder, arXiv:2406.11939). The mapping can be re-tuned without relabelling. |
| 5. Pairwise difficulty | The teacher compares two tasks, order-swapped. A Bradley–Terry model turns the comparisons into a scale. | Pairwise beats absolute ratings (arXiv:2605.18562). Avoids every task scoring 6–7. |
| 6. Two teacher families → soft labels | Keep the label distributions. Relabel only where the teachers disagree. | Soft ensemble labels beat majority vote (GEM 2026). Limits self-preference bias. |
| 7. Dedup + noise cleanup | Embedding near-duplicate removal (SemDeDup), then cleanlab on cross-validated student predictions. | Saves teacher spend and finds teacher errors. |
| 8. Gold set | 200–300 real tasks with real outcomes. **Test only.** | LLM judges agree with each other (α≈0.9) yet correlate only ρ≈0.4 with true difficulty (AIME-Con 2026). |

Licences for the real seeds in step 2, verified: SWE-rebench (CC-BY-4.0, which already includes
difficulty scores), SWE-smith (MIT) and WildChat-1M (ODC-BY). SWE-bench has no dataset licence
tag, so exclude it or use it for evaluation only.

Size: about 10–20k labelled tasks to start. Learning curves on the gold set decide when to stop.
Teacher spend is the only real cost.

### 12.3 Training recipe (Mac M4 Max, PyTorch MPS)

- **Fine-tuning.** Full fine-tune; LoRA underperforms at this size (arXiv:2405.09673). Pooling is
  `classifier_pooling="mean"`. LR is 1e-4 for 17–32M and 5e-5 for 68–150M, with 6% warmup
  followed by linear decay. Batch size 16–32 (Ettin appendix F).
- **Heads.** Category: cross-entropy (CE) on soft labels. Difficulty and the 10 skill axes: CORN
  ordinal heads (`coral-pytorch`). Flags and checklist: binary cross-entropy (BCE). Output tokens:
  quantile loss on log values.
- **Loss.** Sum of the per-head losses, each normalized by its initial value. This matches
  GradNorm/PCGrad (arXiv:2201.04122).
- **Stages.**
  1. Train the 400M teacher.
  2. Cache its logits and embeddings once.
  3. Distil to 32M/68M with KL at T=2–4 per head, plus hard labels.
  4. Train with 3–5 seeds and greedy-soup the weights (arXiv:2203.05482).
  5. Fit a temperature per head on validation.
  6. Export to ONNX with Optimum, with `torch.compile` disabled. Apply int8 and **compare each
     head fp32 vs int8**. Leave the sensitive MatMuls in fp32 if accuracy drops by more than 1 point.
- **Mac specifics.**
  - Use fixed length buckets (64/128/256). This avoids a known MPS SDPA leak with varying lengths
    (pytorch#152550).
  - Use bf16 autocast, with the heads and loss in fp32.
  - Expect no unpadding: FlashAttention is CUDA-only.
  - MLX is optional.

### 12.4 Novel methods we will try

Novelty was checked only lightly against the literature. Where a related method is already
published, it is named.

1. **Outcome-anchored difficulty scale.** Run a ladder of 3–4 real models, from small to
   frontier, on about 300 verifiable seed tasks (SWE-rebench tests). Fit IRT difficulties from
   the results. Then linearly map the teacher's Bradley–Terry scale onto those anchors. Difficulty
   then means "which tier succeeds", which is exactly what routing needs. The same anchors put
   every card's θ on one shared scale.
2. **Counterfactual minimal pairs.** The teacher makes one controlled edit to a task, such as
   adding screenshots, attaching a 200k-token log, removing the acceptance criteria, or adding "and
   a migration plan". The label change is known by construction. Train with a margin ranking loss,
   e.g. `diff(edited) > diff(original)`, plus flag flips. This teaches causal features, not
   surface style, at almost no teacher cost.
3. **Decision-focused training.** Each batch samples random synthetic card pools and routes them
   through a differentiable soft-argmax matcher. The loss adds the expected **routing regret** to
   the per-head losses. Mistakes that would change the picked model cost more than harmless ones.
   This adapts predict-then-optimise / SPO+ from operations research. We found no router that does
   this.
4. **Decision-aware labelling budget.** Spend extra teacher calls (second teacher, pairwise) only
   on tasks where label disagreement **flips the routed model** across sampled pools. Disagreement
   that never changes a decision stays unlabelled. This applies active learning (EvoKD/ELAD style)
   with routing regret as the acquisition function.
5. **Uncertain cards plus bandit-updated θ.** Each card stores θ ± SE per axis. The router samples
   from a softmax over utility and logs the propensity. A nightly job updates θ and its SE from
   outcomes with doubly-robust estimates, so cards sharpen over time without retraining the
   encoder. Bandit routers and point-estimate MIRT routers are both published separately; updating
   IRT card parameters by bandit is not.
6. **Cascade with a difficulty posterior.** When a cheap model fails the verifier, update the
   task's difficulty posterior (b must be > θ_cheap), then re-pick by utility. Today's cascades
   just escalate one tier blindly.
7. **New model in about 30 tasks.** For a new roster model, set a prior from its published scores
   (RouteProfile idea). Then run adaptive testing on the anchor tasks (RADAR, Fluid,
   tinyBenchmarks): about 20–50 items per axis until the standard error on θ is small enough.

### 12.5 Revised phases

| Phase | Deliverable | Exit criteria |
|---|---|---|
| 0 | Schemas, taxonomy, checklist v1, cards with θ ± SE (hand-seeded) | Validate |
| 1 | Matcher in code + heuristic profiler + logging | End-to-end routing |
| 2 | Synthetic dataset (12.2) + 300-task anchor ladder + gold set | Teacher agreement and cost reported; anchors fitted |
| 3 | Ettin-400M teacher → 68M/32M students, calibrated, int8 | Beats kNN and heuristic baselines on the gold set; ECE < 0.05; p50 < 20 ms on CPU |
| 4 | Ablations of the novel methods (12.4 #2–#4) | Keep only what improves gold-set regret |
| 5 | Online loop (12.4 #5–#7) | Replay gate passes |
