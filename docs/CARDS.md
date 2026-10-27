# Model cards

Cards are documented in [cards/README.md](../cards/README.md): the skill scale, provenance of every field, how to
add or edit a card, `supersedes` links, pool name aliases and outcome calibration. The format is defined by
[schemas/model_card.schema.json](../schemas/model_card.schema.json).

Quick reference:

- v4 uses a card in two ways: the 9 cards the learned success head covers get a calibrated P; every other card gets a
  conservative card-prior P that depends on its `provenance` ([how](../cards/README.md#how-the-v4-router-uses-a-card)).

- One file per model, `cards/<id>.json`; `id` must equal the file name. `provider` and `model` say how to invoke it
  (see [INTEGRATIONS.md](INTEGRATIONS.md#mapping-a-pick-to-a-harness)).
- After editing, run `pytest tests/test_matcher.py` (it validates every card). A running server picks up changes
  without a restart.
- Pass only cards you can run in `pool` ([pool hygiene](BEST_RESULTS.md#3-pool-hygiene)); the default pool is all 65.
- Opt in to the free OpenRouter tiers with `--cards cards/optional` or by passing a card inline in `pool`.
