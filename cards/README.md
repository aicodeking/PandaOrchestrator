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
| mid | 7.0–7.7 | gpt-6-luna, gpt-5.6-luna, glm-5.1, haiku-5.5, k2.7-code |
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
| grok-4.6 | benchmark-informed | verified | verified |
| ollama-gemma4-26b (local, cost 0) | estimated | verified | 131072 assumes a raised `OLLAMA_CONTEXT_LENGTH` |

## Added 2026-10-25: OpenRouter and local Ollama

- **26 OpenRouter cards** (`openrouter-*.json`, `provider: "openrouter"`, `model` = OpenRouter slug):
  the most-used models on openrouter.ai/rankings (2-day window). Cost, context, max output, image
  input and tool support are `verified` from `https://openrouter.ai/api/v1/models`. Skills are
  `benchmark-informed` from the Artificial Analysis intelligence/coding/agentic indices OpenRouter
  shows, calibrated against the tiers above; `hy3`, `hy4-preview` and `qwen3.8-flash` are
  `estimated`. Latency is estimated for all. Models that already had a native card are skipped.
- **Free tiers** (`:free` slugs) are in `cards/optional/` and are **not** in the default pool: at
  cost 0 they win almost every cheap route, but they are rate limited and prompts may be logged.
  Opt in with `--cards cards/optional` or by passing the card inline in `pool`.
- **Local Ollama (22 library cards + `ollama-gemma4-26b`):** popular general-purpose models from
  ollama.com/library (Qwen 3.5-3.8, Gemma 4, gpt-oss, Mistral/Ministral/Devstral, Phi-4, GLM-4.7-flash,
  Qwen3-Coder, Nemotron, OLMo, Granite, Llama 3.1), 1-3 sizes each, Q4 default tags. `:cloud` tags are
  skipped. Tagged `not-installed`: `ollama pull <model>` first, or keep them out of `pool`. Latency is
  scaled from the measured gemma4:26b (78 tok/s) by active params; context capped at 131072.
- Cheapest mode breaks cost ties (e.g. all local models at $0) by **lowest latency**, then P.

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

## Newer versions win (`supersedes`)

A card may list older versions of the same model line in `supersedes` (same provider, same
size/tier, higher version number). When the newer card and an older one both pass the filters, the
older one is dropped with reason `superseded_by:<newer>` **if the newer one costs the same or less
for this task**. A pricier successor competes normally, so the cheaper older version can still win
when it clears the success threshold. The older card is
used only when its successor is not in the pool or is filtered out (excluded, too small a context,
missing a feature...). Current links:

| newer | supersedes |
|---|---|
| grok-4.6 | grok-4.5 |
| codex-gpt-6-luna | codex-gpt-5.6-luna |
| glm-5.1 | glm-4.7 |
| openrouter-gpt-6.1-sol | openrouter-gpt-6-sol |
| openrouter-deepseek-v4.1-flash | openrouter-deepseek-v4-flash |
| ollama-qwen3.8-27b | ollama-qwen3.6-27b, ollama-qwen3.5-27b |
| ollama-nemotron-3.5-lightning-30b | ollama-nemotron-3-nano-30b |

Not linked on purpose: different lines or tiers (flash vs pro, turbo, air, code, highspeed),
different sizes, and the same model through a different harness (native grok-4.6 vs
openrouter-grok-4.7). `openrouter-gpt-6-sol`, `ollama-qwen3.{5,6}-27b` and
`ollama-nemotron-3-nano-30b` were rebuilt on 2026-10-26 from their successors' cards.

## Names in `pool`

`pool` entries don't have to be exact card ids. The router matches, in order: exact id; exact
`model` (pull name / slug, also after a `vendor/` prefix); case- and separator-insensitive id or
model (`claude/sonnet-5-5`); then the closest spelling with the **same version digits**
(`claude-haikuu-5.5`). Responses always echo the caller's string as `model_id` and add `card_id`
for the card it was scored as. Names that stay ambiguous (`qwen3.8-27b`: Ollama or OpenRouter?) or
have no close match with the same digits (`claude/sonnet-4-5`) are returned in `filtered_out` as
`unknown_model`.
