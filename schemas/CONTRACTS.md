# Panda Router: shared contracts (v1)

Every component MUST follow this file and `schemas/taxonomy.json`. Change them only through the architect.

## Environment

- Python env: `.venv/` (Python 3.12, created with uv). Run `.venv/bin/python`.
- Add packages with `uv pip install --python .venv/bin/python <pkg>`. Note every addition in the
  worker report.
- Package code lives in `panda_router/` and is importable as `panda_router`. Tests go in `tests/`
  and run with `.venv/bin/python -m pytest`.
- Large artefacts (`data/raw`, `data/cache`, `artifacts/`, `checkpoints/`) are gitignored.

## Teacher LLMs (for synthetic data)

Claude Code is disabled for this org. Do not use it. Available teachers:

- **Codex CLI**: `codex exec --skip-git-repo-check -m gpt-5.6-luna "<prompt>"`. The final answer
  is printed last on stdout. Each call carries about 17k tokens of harness overhead, so batch many
  items per call.
- **Kimi CLI**: `kimi -p "<prompt>"`, non-interactive.
- **Ollama, local**: model `gemma4:26b` at `http://localhost:11434/api/generate`. Free but slow.
  Use it as the tie-breaker or third teacher family.

## Task input (what the profiler reads)

```json
{ "text": "task text", "context": { "repo_languages": ["python"], "files_in_scope": 3,
  "estimated_input_tokens": 4000, "has_images": false, "requires_tools": true } }
```

The model input string is built ONLY by `panda_router.text.format_input(task: dict) -> str`.
Training and serving must both use this one function.

## Labelled example: `data/<split>.jsonl`, one JSON object per line

```json
{
  "id": "syn-000123",
  "source": "synthetic | swe-rebench | wildchat | swe-smith | minimal-pair",
  "pair_of": null,
  "task": { "text": "...", "context": { } },
  "labels": {
    "category": { "implementation": 0.8, "refactor": 0.2 },
    "difficulty": [0,0,0.05,0.2,0.5,0.2,0.05,0,0,0],
    "skills": { "coding": [11 floats, levels 0..10], "debugging": [...] },
    "flags": { "needs_tools": 0.95 },
    "checklist": { "edits_code": 1.0 },
    "out_tokens_log10": 3.4
  },
  "meta": { "teachers": ["codex", "kimi"], "agreement": 0.83, "persona": "terse SRE" }
}
```

Field rules:

- `category` is a probability distribution over taxonomy categories that sums to 1. Omitted
  categories mean 0.
- `difficulty` is a length-10 distribution over levels 1..10.
- `skills` has every axis, each a length-11 distribution over levels 0..10.
- `flags` and `checklist` have every id, each a probability in [0, 1].
- `out_tokens_log10` is log10 of the expected output tokens of a competent model.
- Soft labels: average the teachers' point answers, then apply light smoothing (σ=0.6 level
  Gaussian) for the ordinal fields.
- **Minimal pairs**: `source="minimal-pair"`, `pair_of=<original id>`, plus
  `meta.edit`, `meta.expected_delta` (for example
  `{"difficulty": "+", "flags.long_context": 1}`).
- Splits are `train`, `val`, `test` (synthetic) and `gold` (real tasks only, never used for
  training). Split by **seed cluster**, so near-duplicates never cross splits.

## Profiler output: `TaskProfile`

`panda_router.profile.TaskProfile`, returned by the trained model and by the heuristic fallback:

```json
{ "category": {"implementation": 0.9, "...": 0.1},
  "difficulty": [10 probs], "skills": {"coding": [11 probs], "...": []},
  "flags": {"needs_tools": 0.97}, "checklist": {"edits_code": 0.99},
  "out_tokens_log10": {"p10": 2.9, "p50": 3.4, "p90": 3.9} }
```

The profiler interface is `Profiler.profile(task: dict) -> TaskProfile`. There are
implementations for ONNX, PyTorch and the heuristic.

## Model card

As in PLAN.md §3.1, except `capabilities` becomes `skills`:
`{ "<axis>": {"theta": 0..10, "se": float} }` on the **same 0..10 scale as the skill levels**.
Optional `discrimination` (a_i, default 1.2).

## Matcher (PLAN.md §12.1)

- `w_k = E[skill_k] / Σ E[skill]` over the axes. If every expected skill is ≈ 0, use the
  `reasoning` axis.
- Effective ability: `θ_eff = Σ_k w_k θ_k`.
- Bottleneck penalty: `pen = λ · Σ_k w_k · max(0, E[skill_k] − θ_k)` with λ = 0.5.
- `P_i = E_{b ~ difficulty dist, θ ~ N(θ, se)} sigmoid(a_i · (θ_eff − pen − b))`, computed by
  quadrature or a fixed-sample Monte-Carlo with a fixed seed.
- Then the filters, utility, modes, floor and fallback from PLAN.md §4. Expected cost uses
  `10**out_tokens_log10.p50`.
- The output is a `RouteResponse` (PLAN.md §3.3).

## Novelty methods in v1 scope

- Minimal pairs, with a margin ranking loss on difficulty and the flags.
- Decision-focused regret loss, using random synthetic card pools and a soft-argmax matcher in
  torch that mirrors the formula above.
- Uncertain cards (θ ± se), integrated in the matcher.
- Cascade difficulty-posterior update: `matcher.escalate(response, failed_model_id)`.
