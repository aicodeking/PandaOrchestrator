# API reference

Four ways in, one engine: HTTP, CLI, Python (`Router`) and MCP. All use the same request and response shapes.
JSON Schemas live in [schemas/](../schemas/): [route_request](../schemas/route_request.schema.json),
[route_response](../schemas/route_response.schema.json), [route_outcome](../schemas/route_outcome.schema.json),
[model_card](../schemas/model_card.schema.json).

Examples below were run against `artifacts/panda-router-v4` (see the README for where the profiler comes from).

## HTTP

```sh
panda-router-serve --port 8765 --artifacts artifacts/panda-router-v4 [--host 127.0.0.1] [--db PATH] [--cards DIR]
```

The server binds to `127.0.0.1` by default and has no authentication. Do not expose it to a network
without a proxy in front. Request bodies over 4 MiB get `413`. Errors are `{"error": "..."}` with `400` for bad
input, `404` for unknown paths, `500` for internal errors.

### `GET /health`

```sh
curl -s localhost:8765/health
```
```json
{"ok": true, "version": "panda-router-0.1.0", "profiler": "OnnxProfiler(panda-router-v4/model.int8.onnx)", "cards": 65, "db": "/tmp/pr-docs.sqlite", "policy": "v4", "success_head": "success_head_v4(panda-router-v4)"}
```

### `POST /route`

Body is a RouteRequest ([schema](../schemas/route_request.schema.json)). Only `task.text` is required.

| field | type | notes |
|---|---|---|
| `task.text` | string, **required** | the task. Over 6,000 characters it is cut to the first and last 3,000 for the profiler |
| `task.kind_hint` | string | used by the heuristic profiler only; the ONNX profiler ignores it |
| `task.context.repo_languages` | string[] | profiler input |
| `task.context.files_in_scope` | int | profiler input |
| `task.context.estimated_input_tokens` | int | profiler input, cost estimate and context filter. Default: text length / 4 + 500 |
| `task.context.has_images` | bool | hard filter: only vision-capable cards |
| `task.context.requires_tools` | bool | hard filter: only tool-capable cards |
| `pool` | array | card ids, model names/aliases, or inline model cards. Default: every card in `cards/` (65). Pass only models you can run |
| `constraints.max_cost_usd` | number | filters cards whose estimated cost for this task is higher |
| `constraints.max_latency_ms` | number | same, for estimated latency |
| `constraints.local_only` | bool | only local (Ollama) cards |
| `constraints.require` | string[] | any of `tools`, `vision`, `json_mode`, `web` |
| `constraints.exclude` | string[] | pool names never to pick |
| `preferences.mode` | enum | `max_utility` (default), `cheapest_above_threshold`, `max_quality`; see [Modes](#modes) |
| `preferences.min_p_success` | 0-1 | threshold for `cheapest_above_threshold` only. Default 0.5 |
| `preferences.floor` | 0-1 | default 0.55. In v4 it only sets `fallback.low_confidence` (pick's P below the floor) |
| `preferences.default_model` | string | reported in `fallback.default_model` when it is in the pool (v4 never falls back to it) |
| `preferences.weights` | object | `quality`, `cost`, `latency`; `max_utility` weights. Default 1.0 / 0.3 / 0.0 |
| `preferences.explore_epsilon`, `explore_temperature`, `seed` | numbers | optional softmax exploration over utility. Default off (epsilon 0); it sets `propensity` and `explored` |
| `questions` | string[] | any of `choice`, `difficulty`, `flags`, `category`, `profile`; add `profile` to get the full TaskProfile |
| `return_top_k` | int 1-50 | ranking length (default 3) |

Other policy constants (`failure_penalty_usd` 0.02, `equal_p_margin` 0.05, `ladder_lambda` 3.0) also read from
`preferences`, but they are tuned values and not in the schema. Leave them alone.

```sh
curl -s -X POST localhost:8765/route -H 'content-type: application/json' -d '{
  "task": {"text": "Migrate our Express auth middleware to use JWT refresh tokens and update all call sites",
           "context": {"repo_languages": ["typescript"], "files_in_scope": 12}},
  "pool": ["claude-sonnet-5.5", "claude-haiku-5.5", "codex-gpt-6-luna", "ollama-qwen3-coder-30b"],
  "preferences": {"mode": "cheapest_above_threshold", "min_p_success": 0.5},
  "constraints": {"max_cost_usd": 0.05},
  "return_top_k": 2
}'
```

Real response (`distribution` shortened, `p_success_note` cut; the router profiled this at difficulty 5):

```json
{
  "choice": {"model_id": "claude-sonnet-5.5", "confidence": 0.6227, "confidence_lower": 0.5427,
             "decided_by": "policy:cheapest_above_threshold", "propensity": 1.0, "explored": false},
  "ranking": [
    {"model_id": "claude-sonnet-5.5", "card_id": "claude-sonnet-5.5", "p_success": 0.6227, "p_success_lower": 0.5427,
     "p_source": "success_head", "quality": 0.8439, "utility": 0.2983, "est_cost_usd": 0.018252,
     "est_cost_to_success_usd": 0.029312, "expected_cost_usd": 0.027815, "est_latency_ms": 21146.7},
    {"model_id": "claude-haiku-5.5", "card_id": "claude-haiku-5.5", "p_success": 0.5042, "p_success_lower": 0.4565,
     "p_source": "success_head", "quality": 0.7972, "utility": 0.2659, "est_cost_usd": 0.000913,
     "est_cost_to_success_usd": 0.00181, "expected_cost_usd": 0.021702, "est_latency_ms": 11923.1}
  ],
  "filtered_out": [],
  "difficulty": {"level": 5, "expected": 4.89, "distribution": [0.015069, 0.046098, "..."],
                 "raw_expected": 4.89, "vagueness": 0.0, "decision_level": 5.382},
  "category": {"label": "implementation", "p": 0.7906},
  "flags": {"needs_tools": 0.479, "needs_vision": 0.0043, "long_context": 0.0089, "needs_review": 0.6681,
            "ambiguous_spec": 0.8646, "multi_file": 0.8993, "needs_web": 0.0728},
  "fallback": {"triggered": false, "floor": 0.55, "default_model": null, "low_confidence": false},
  "router": {"version": "panda-router-0.1.0", "profiler": "OnnxProfiler(panda-router-v4/model.int8.onnx)",
             "latency_ms": 10.228, "pool_hash": "ca3ba9bbba9837d7", "policy": "v4",
             "success_head": "success_head_v4(panda-router-v4)", "p_success_note": "p_success: estimated pass rate ..."},
  "trace_id": "r_dc1daf912043483d80cdd510",
  "escalation_ladder": [
    {"model_id": "claude-haiku-5.5", "p_success": 0.5042, "p_success_lower": 0.4565, "est_cost_usd": 0.000913},
    {"model_id": "claude-sonnet-5.5", "p_success": 0.6227, "p_success_lower": 0.5427, "est_cost_usd": 0.018252},
    {"model_id": "codex-gpt-6-luna", "p_success": 0.3093, "p_success_lower": 0.2727, "est_cost_usd": 0.000913}
  ],
  "escalation_ladder_note": "try in order, escalate on failure; independent-failure estimate of success within 2 attempts >= 0.75"
}
```

Note that `choice` (sonnet) and `escalation_ladder[0]` (haiku) can differ. `choice` is the best single shot for the
mode; the ladder is the best *sequence* if you will verify and retry.

Response fields:

| field | meaning |
|---|---|
| `choice.model_id` | the pick, as the caller wrote it in `pool` (`null` if everything was filtered out) |
| `choice.confidence` | `p_success` of the pick |
| `choice.confidence_lower` | its lower bound, `p_success_lower` (v4) |
| `choice.decided_by` | see [decided_by](#decided_by) |
| `choice.propensity`, `explored` | exploration info; 1.0 / false unless `explore_epsilon` > 0 |
| `ranking[]` | the pick first, then the rest by `p_success`. See below |
| `ranking[].model_id` | your string from `pool` |
| `ranking[].card_id` | the card it was scored as. Differs from `model_id` when you used an alias (`claude/sonnet-5-5` -> `claude-sonnet-5.5`) |
| `ranking[].p_success` | **calibrated strict-grading pass rate**: the chance that an LLM judge grading strictly passes this model's answer to a task like this, calibrated per model on graded train/val attempts (ECE 0.015 there). Not the odds that your own tests pass |
| `ranking[].p_success_lower` | the decision bound: a lower confidence bound on `p_success`. Policies decide on this, not on `p_success` |
| `ranking[].p_source` | `success_head` (the learned head covers this card) or `card_prior` (any other card: its skill profile, shrunk toward the covered cards and penalised by provenance; $0 and local cards get an extra penalty) |
| `ranking[].quality` | card ability on this task's skills, 0-1 |
| `ranking[].utility` | the `max_utility` score |
| `ranking[].est_cost_usd` | estimated cost of one call: input tokens x price in + predicted output tokens x price out |
| `ranking[].expected_cost_usd` | `est_cost_usd` + P(fail) x (cost of the next-best model + $0.02): the cost including failure |
| `ranking[].est_cost_to_success_usd` | `est_cost_usd / p_success` |
| `ranking[].est_latency_ms` | time to first token + output tokens / speed, from the card |
| `escalation_ladder[]` | models in the order to try, `model_id`, `p_success`, `p_success_lower`, `est_cost_usd`. The first two entries are the ordered pair with the best chance of passing within two attempts minus a cost term (the second is scored given that the first failed); the third is the most likely remaining model. Up to 3 entries. A $0 or local model can open it only if it is close to the best paid model. Absent when everything is filtered out |
| `escalation_ladder_note` | text including an independent-failure estimate of success within 2 attempts. Failures are correlated, so treat it as optimistic |
| `filtered_out[]` | `model_id` and `reason`: `unknown_model`, `superseded_by:<id>`, `escalation:failed`, `constraint:max_cost_usd`, `constraint:local_only`, `constraint:exclude`, `constraint:require=<f>`, `profile:needs_tools`, `profile:needs_vision`, `limit:context`. Several reasons join with `;` |
| `difficulty` | `level` (argmax of the decision distribution), `expected`, 10-bin `distribution`; v4 adds `raw_expected` (profiler only), `vagueness` (0-1) and `decision_level` (the quantile the card calibration uses) |
| `category`, `flags` | most likely category with probability; flag probabilities |
| `fallback` | `triggered` (true only when no model survived the filters), `floor`, `default_model`, `reason`, `low_confidence` (pick's `p_success` is below `floor`) |
| `router` | `version`, `profiler`, `latency_ms`, `pool_hash`, `policy` (`v4`), `success_head` (the head's name, `null` if disabled), `p_success_note` |
| `profile` | the full TaskProfile, only if `questions` includes `profile` |
| `trace_id` | pass to `/outcome` and `/escalate` |

The response contains the card id (`card_id`), not the card's `provider` or `model`. To invoke the model, look the
card up in `cards/<card_id>.json`, use the MCP `list_models` tool, or `router.matcher.cards[card_id]` in Python.
See [INTEGRATIONS.md](INTEGRATIONS.md#mapping-a-pick-to-a-harness).

#### Modes

Every mode ranks candidates by the lower bound `p_success_lower`, after the filters above. A $0 or local model may
win only if its lower bound is within 0.05 of the best paid model's. Expected cost is
`E = cost + (1 - P) * (cost of the next-best model + failure_penalty_usd)`, with `failure_penalty_usd` = 0.02.

| mode | rule |
|---|---|
| `max_quality` | highest `p_success_lower`. Models within 0.01 of the best count as tied and the cheaper wins |
| `cheapest_above_threshold` | lowest `E` among models with `p_success_lower` >= `min_p_success` (ties within 2% go to the stronger). If no model qualifies, the `max_quality` pick, with `decided_by` ending `:relaxed` |
| `max_utility` (default) | highest `quality_w * p_lower - cost_w * E / max(E) - latency_w * latency / max(latency)`; weights 1.0 / 0.3 / 0.0 |

For `cheapest_above_threshold` and `max_utility`, a final pass swaps in a cheaper model (cost at least 2% lower) when
its calibrated `p_success` is within `equal_p_margin` (0.05) of the pick's and its lower bound is not more than 0.05
below the pick's. For `cheapest_above_threshold` the swap stays among models that meet `min_p_success`. The result is
marked `:equal_p_cheaper`.

Measured single pick, 150 held-out tasks, 9-model pool: `max_utility` 77.3 @ $0.99 per 100 tasks, `max_quality`
82.0 @ $1.20, `cheapest_above_threshold` 74.0 @ $0.74. Which to use: [BEST_RESULTS.md](BEST_RESULTS.md#2-choosing-a-mode).

#### decided_by

| value | meaning |
|---|---|
| `policy:max_utility`, `policy:max_quality`, `policy:cheapest_above_threshold` | the mode's rule picked it |
| `policy:cheapest_above_threshold:relaxed` | nothing met `min_p_success`; this is the `max_quality` pick. At the default 0.5 it appears on hard or vague tasks; at 0.75 it is common |
| `policy:<mode>:equal_p_cheaper` | a cheaper model had nearly the same P (see above), `max_utility` or `cheapest_above_threshold` |
| `escalation_ladder` | returned by `/escalate`: the first ladder model that has not failed |
| `explore:softmax(eps=...)` | exploration drew a non-greedy pick |
| `none:all_filtered` | no model survived the filters; `choice.model_id` is `null` |

Pool names resolve to cards: unknown or ambiguous names are skipped and listed in `filtered_out` as `unknown_model`. A
bad request body (for example no `task.text`) returns `400` with `{"error": "invalid route_request: task: 'text' is a
required property"}`.

### `POST /escalate`

A model failed; get the next pick. The failure is evidence the task is harder: the difficulty posterior shifts up,
every model that failed is excluded, and the pick follows the `escalation_ladder` of the response you send.

Body: `{"request": <the original RouteRequest>, "response": <the latest RouteResponse>, "failed_model_id": "<id>"}`.
`failed_model_id` must be in the pool. The server reuses the cached profile if it still has the `response.trace_id`
(last 1024 routes), otherwise it re-profiles.

```sh
curl -s -X POST localhost:8765/escalate -H 'content-type: application/json' \
  -d '{"request": {...}, "response": {...}, "failed_model_id": "claude-haiku-5.5"}'
```

The reply is a RouteResponse with a new `trace_id`, an `escalation` object (`parent_trace_id`, `failed_models`,
`prior_difficulty`, `posterior_difficulty`), the failed models in `filtered_out` (`escalation:failed`), and a
**recomputed** `escalation_ladder` for the remaining models. Pass this response, not the original, to the next
`/escalate`. Real output after `claude-haiku-5.5` failed on the first example (distributions and ranking omitted):

```json
{"choice": {"model_id": "claude-sonnet-5.5", "confidence": 0.5627, "confidence_lower": 0.4809,
            "decided_by": "escalation_ladder", "propensity": 1.0, "explored": false},
 "escalation": {"parent_trace_id": "r_3ebd4fa7eced4838b54c804c", "failed_models": ["claude-haiku-5.5"], "...": "..."},
 "filtered_out": [{"model_id": "claude-haiku-5.5", "reason": "escalation:failed"}],
 "escalation_ladder": [{"model_id": "codex-gpt-6-luna", "p_success": 0.3039, "...": "..."},
                       {"model_id": "claude-sonnet-5.5", "p_success": 0.5627, "...": "..."},
                       {"model_id": "ollama-qwen3-coder-30b", "p_success": 0.1495, "...": "..."}],
 "escalation_ladder_note": "try in order, escalate on failure; independent-failure estimate of success within 2 attempts >= 0.62"}
```

If you fail the `choice` and the previous ladder opened with a different, untried model, `/escalate` returns that
model (here: failing `claude-sonnet-5.5` returned `claude-haiku-5.5`). Run `escalation_ladder[0]` first to keep
retries moving up. If every remaining model is filtered out, `choice.model_id` is `null`.

### `POST /outcome`

Log what happened. Required: `trace_id`, `model_id`, `success`. Log every attempt, failures included. Returns
`{"ok": true, "id": <row>, "trace_id": ...}`.

| field | type |
|---|---|
| `trace_id` | string, from the route or escalate response the model was picked in |
| `model_id` | string, the model you ran |
| `success` | boolean |
| `propensity` | number 0-1 or null |
| `signals` | `{tests_passed: bool, review_verdict: string, retries: int, user_override: string}` |
| `quality` | number 0-1 |
| `actual_cost_usd`, `actual_latency_ms` | number >= 0 |
| `tokens` | `{"in": int, "out": int}` |

```sh
curl -s -X POST localhost:8765/outcome -H 'content-type: application/json' \
  -d '{"trace_id":"r_3f932d79b10f4edba6c7e6a6","model_id":"claude-sonnet-5.5","success":true,"signals":{"tests_passed":true,"retries":1},"actual_cost_usd":0.02,"actual_latency_ms":21000}'
# {"ok": true, "id": 1, "trace_id": "r_3f932d79b10f4edba6c7e6a6"}
```

Routes and outcomes are stored in SQLite (`--db`, else `$PANDA_ROUTER_DB`, else `data/cache/router_log.sqlite`).
Outcomes are logged for later fitting; the running router does not change its picks from them. See
[BEST_RESULTS.md](BEST_RESULTS.md#6-send-outcomes).

## CLI

`panda-router route` (same as `python -m panda_router.serve.cli route`) routes one task and prints the RouteResponse.
Exit code 2 and `{"error": ...}` on stderr for invalid input.

| flag | meaning |
|---|---|
| `--task TEXT` | **required** task text |
| `--context JSON` | `task.context` as JSON |
| `--kind-hint S` | `task.kind_hint` |
| `--pool a,b,c` | comma-separated card ids or names (default: all cards) |
| `--mode M` | `cheapest_above_threshold`, `max_utility`, `max_quality` (default `max_utility`) |
| `--min-p P` | `preferences.min_p_success` (only used by `cheapest_above_threshold`; default 0.5) |
| `--max-cost USD` | `constraints.max_cost_usd` |
| `--local-only` | only local (Ollama) cards |
| `--top-k N` | ranking length (default 3) |
| `--profile` | include the full TaskProfile |
| `--artifacts DIR` | ONNX profiler directory (default: `$PANDA_ROUTER_ARTIFACTS`, else `artifacts/panda-router-v4` in a source checkout, else the weaker heuristic profiler) |
| `--cards DIR` | cards directory (default `cards/`) |
| `--db PATH` | SQLite log path |
| `--no-log` | do not write the route to SQLite |

The CLI has no escalate or outcome command; use HTTP, MCP or Python.

Server flags (`panda-router-serve`): `--host`, `--port`, `--artifacts`, `--db`, `--cards`.

## Python

```python
from panda_router.serve.router import Router, load_profiler

router = Router(profiler=load_profiler("artifacts/panda-router-v4"), db_path="/tmp/router.sqlite")
req = {"task": {"text": "Add retry with backoff to the S3 uploader"},
       "pool": ["claude-sonnet-5.5", "claude-haiku-5.5", "ollama-qwen3-coder-30b"]}

resp = router.route(req)
card = router.matcher.cards[resp["choice"]["model_id"]]       # keyed by card id
print(resp["choice"]["model_id"], card["provider"], card["model"], resp["trace_id"])
# claude-haiku-5.5 claude claude-haiku-5-5 r_aeaf1d93488c4a62a4e7ab2f

first = resp["escalation_ladder"][0]["model_id"]             # run this one first, verify, and on a failure:
nxt = router.escalate(req, resp, first)                       # nxt["choice"]["model_id"] == "claude-sonnet-5.5"
router.record_outcome({"trace_id": nxt["trace_id"], "model_id": nxt["choice"]["model_id"], "success": True})
```

- `Router(profiler=None, matcher=None, db_path=None, cards_dir=None, log_routes=True)`. With no profiler it uses the
  heuristic profiler.
- `load_profiler(dir)` loads the ONNX profiler and raises if it cannot; `load_profiler(None)` returns the heuristic.
- `route(request)`, `escalate(request, response, failed_model_id)`, `record_outcome(outcome)`, `health()`.
  For a non-default head or policy pass `matcher=Matcher(success_head=..., policy="v4"|"v3")`; the defaults are
  the shipped v4 head and policy. Set `PANDA_ROUTER_SUCCESS_HEAD=off` to disable the head, or to a path to use another.
- Invalid input raises `panda_router.serve.router.RequestError`. `router.matcher.cards` maps card id to the card dict
  (indexing with a pool alias that is not a card id raises `KeyError`; use `response["ranking"][i]["card_id"]`).

## MCP (stdio)

```sh
panda-router-mcp [--artifacts DIR] [--cards DIR] [--db PATH]
```

Env equivalents: `PANDA_ROUTER_ARTIFACTS`, `PANDA_ROUTER_CARDS`, `PANDA_ROUTER_DB`. If `--artifacts` is absent it uses
`artifacts/panda-router-v4` in the source checkout when present, otherwise the heuristic profiler (with a warning on
stderr). Newline-delimited JSON-RPC 2.0, protocol version `2025-06-18`, tools only. Logs go to stderr.

| tool | arguments | returns |
|---|---|---|
| `route_task` | `task_text` (required), `context`, `pool[]`, `mode`, `min_p_success`, `max_cost_usd`, `local_only`, `require[]`, `exclude[]`, `top_k` | text summary (`model=... P(success)=... difficulty=... category=... trace_id=...`) and the full RouteResponse as `structuredContent` |
| `escalate_task` | `trace_id`, `failed_model_id` (both required) | same as `route_task`, for the next pick. The `trace_id` must come from a route logged in the same database |
| `record_outcome` | `trace_id`, `model_id`, `success` (required); `cost_usd`, `latency_ms`, `notes` | `recorded outcome for <trace_id> (id=N)` |
| `list_models` | none | `{"models": [{id, provider, model, cost, local, description}]}` |

Tool-level failures (bad arguments, unknown `trace_id`) return `isError: true` with an `error: ...` message rather
than a protocol error. `route_task` and `escalate_task` return the full RouteResponse, including
`escalation_ladder`, in `structuredContent`; the text line shows only the pick. Real transcript from a stdio run
(`route_task` with a 3-model Claude pool, `escalate_task` after the ladder's first model failed, `record_outcome`,
then an unknown trace):

```
model=claude-sonnet-5.5 P(success)=0.778 difficulty=4 category=bugfix trace_id=r_6c1d845de34e47e99c73fc22
  structuredContent.escalation_ladder: claude-haiku-5.5, claude-sonnet-5.5, claude-opus-5.5
model=claude-sonnet-5.5 P(success)=0.764 difficulty=8 category=bugfix trace_id=r_76774f47de6c4acd9fe21bb3
  structuredContent.choice.decided_by: escalation_ladder
recorded outcome for r_76774f47de6c4acd9fe21bb3 (id=1)
error: unknown trace_id (routes must be logged) or missing failed_model_id      (isError: true)
```

The difficulty went from 4 to 8 after the failure: the failure is treated as evidence that the task is harder.
How an agent should use these tools in a loop: [BEST_RESULTS.md](BEST_RESULTS.md#mcp-agent-driven).
