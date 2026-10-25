# Model cards

One JSON file per routable model, named `<id>.json`. Every file must validate against
`schemas/model_card.schema.json`; `panda_router.matcher.load_cards()` refuses to load invalid cards.

## Skill scale

`skills.<axis>.theta` is on the **same 0..10 scale as the profiler's skill levels and difficulty**
(`schemas/taxonomy.json`): difficulty 5 = "mid-tier model usually succeeds", 8 = "only frontier
models usually succeed". The matcher computes
`P = E_{b, θ~N(θ,se)} sigmoid(a·(Σ w_k θ_k − 0.5·Σ w_k max(0, E[skill_k] − θ_k) − b))`, so a model
with θ = b succeeds 50% of the time, and θ − b = 2 gives about 92% at the default
`discrimination` a = 1.2. `se` is the uncertainty; larger `se` moves P toward 0.5.

Rough anchors used for the hand-seeded thetas (Oct 2026):

| Tier | coding θ | Examples |
|---|---|---|
| frontier | 9.0–9.3 | claude-opus-5.5, claude-fable-5.1 |
| strong | 8.0–8.6 | claude-sonnet-5.5, gpt-5.6-terra, grok-4.6, kimi-k3 |
| mid | 7.0–7.7 | gpt-6-luna, gpt-5.6-luna, glm-5.1, grok-4.5, haiku-5.5, k2.7-code |
| small | 5.0–6.5 | glm-4.7, glm-4.5-air, local gemma4:26b |

## Provenance

- `provenance` summarises how the **skills** were set:
  - `benchmark-informed`: ordered and spaced using public benchmarks (SWE-bench Verified, Real-SWE,
    vendor claims). SWE-bench Verified is saturated (>90%) and harness-dependent, so it only orders
    models; `se` is 0.5–0.9.
  - `estimated`: no usable independent benchmark found. Conservative guess with `se >= 1.5`.
  - `verified`: reserved for thetas fitted from our own eval harness (PLAN.md §12.4 #1, #7).
- `field_provenance` gives the status per field group (`cost`, `limits`, `skills`, `latency`).
  Prices and context limits were checked against vendor pages on 2026-10-25 (`sources`). Latency
  (`ttft_ms_p50`, `tokens_per_sec`) is estimated unless marked otherwise.
- `notes` records caveats (long-context price tiers, assumed context windows, deprecations).

Summary at creation (2026-10-25):

| Card | skills | cost | limits |
|---|---|---|---|
| claude-opus-5.5, claude-sonnet-5.5, claude-haiku-5.5, claude-fable-5.1 | benchmark-informed | verified | verified |
| codex-gpt-6-luna | benchmark-informed | verified | verified |
| codex-gpt-5.6-terra, codex-gpt-5.6-luna | benchmark-informed | verified | estimated (400k assumed) |
| kimi-k3 | benchmark-informed | Bedrock list price (native table unreadable) | verified |
| kimi-k2.7-code, kimi-k2.7-code-highspeed | estimated | verified | verified |
| glm-5.1 | benchmark-informed (vendor parity claim with Opus 4.6) | verified | verified |
| glm-5-turbo, glm-4.5-air | estimated | verified | verified |
| glm-4.7 | estimated | verified | estimated |
| grok-4.6, grok-4.5 | benchmark-informed | verified | verified |
| ollama-gemma4-26b (local, cost 0) | estimated | verified | 131072 assumes a raised `OLLAMA_CONTEXT_LENGTH` |

## Adding a model

1. Copy the closest existing card to `cards/<id>.json`. The `id` must match the file name and is
   what the orchestrator dispatches on.
2. Fill `cost` (USD per million tokens, base tier), `limits.context_tokens`, `modalities.input`
   (add `"image"` only if it accepts images), `features.tools`, `latency`, `local`.
3. Set `skills` for every axis. Without evidence, copy a similar model, subtract a little, set
   `se >= 1.5` and `"provenance": "estimated"`. Missing axes are allowed: the matcher fills them with
   the card's mean θ − 0.5 and a wide `se`.
4. Record `sources`, `field_provenance` and caveats in `notes`.
5. Run `.venv/bin/python -m pytest tests/test_matcher.py` (it validates every card).

The router picks up new or changed cards without a restart (cache keyed on file mtimes; compiled
pools are cached by pool hash). Later, the probe-set procedure in PLAN.md §12.4 #7 replaces the
estimates with fitted θ ± se.
