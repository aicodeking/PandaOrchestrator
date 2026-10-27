# API reference

Four ways in, one engine: HTTP, CLI, Python (`Router`) and MCP. All use the same request and response shapes.
JSON Schemas live in [schemas/](../schemas/): [route_request](../schemas/route_request.schema.json),
[route_response](../schemas/route_response.schema.json), [route_outcome](../schemas/route_outcome.schema.json),
[model_card](../schemas/model_card.schema.json).

Examples below were run against `artifacts/panda-router-v3` (see the README for where the profiler comes from).

## HTTP

```sh
panda-router-serve --port 8765 --artifacts artifacts/panda-router-v3 [--host 127.0.0.1] [--db PATH] [--cards DIR]
```

The server binds to `127.0.0.1` by default and has no authentication. Do not expose it to a network
without a proxy in front. Request bodies over 4 MiB get `413`. Errors are `{"error": "..."}` with `400` for bad
input, `404` for unknown paths, `500` for internal errors.

### `GET /health`

```sh
curl -s localhost:8765/health
```
```json
{"ok": true, "version": "panda-router-0.1.0", "profiler": "OnnxProfiler(panda-router-v3/model.int8.onnx)", "cards": 65, "db": "/tmp/pr-docs.sqlite"}
```

### `POST /route`

Body is a RouteRequest.

| field | type | notes |
|---|---|---|
| `task.text` | string, **required** | the task |
| `task.kind_hint` | string | optional hint |
| `task.context` | object | `repo_languages[]`, `files_in_scope`, `estimated_input_tokens`, `has_images`, `requires_tools` |
| `pool` | array | card ids, model names/aliases, or inline model cards. Default: every card in `cards/` |
| `constraints` | object | `max_cost_usd`, `max_latency_ms`, `local_only`, `require[]` (`tools`, `vision`, `json_mode`, `web`), `exclude[]` |
| `preferences.mode` | enum | `max_utility` (default), `cheapest_above_threshold`, `max_quality` |
| `preferences` | object | `min_p_success`, `floor`, `default_model`, `weights{quality,cost,latency}`, `explore_epsilon`, `explore_temperature`, `seed` |
| `questions` | array | any of `choice`, `difficulty`, `flags`, `category`, `profile`; add `profile` to get the full TaskProfile |
| `return_top_k` | int 1-50 | ranking length |

```sh
curl -s -X POST localhost:8765/route -H 'content-type: application/json' -d '{
  "task": {"text": "Fix the flaky test in tests/test_queue.py"},
  "pool": ["claude-sonnet-5.5", "claude-haiku-5.5", "codex-gpt-6-luna"],
  "preferences": {"mode": "cheapest_above_threshold", "min_p_success": 0.8},
  "constraints": {"max_cost_usd": 0.05},
  "return_top_k": 2
}'
```

Response fields:

| field | meaning |
|---|---|
| `choice.model_id` | the pick, as the caller wrote it in `pool` (null if everything was filtered out) |
| `choice.confidence`, `decided_by`, `propensity`, `explored` | P(success) of the pick, the policy that chose it (`policy:...` or `fallback:...`), exploration info |
| `ranking[]` | `model_id`, `card_id`, `p_success`, `quality`, `utility`, `est_cost_usd`, `est_cost_to_success_usd`, `est_latency_ms` |
| `filtered_out[]` | `model_id` and `reason` (`superseded_by:<id>`, `unknown_model`, context/feature/constraint reasons) |
| `difficulty` | `level` 1-10, `expected`, 10-bin `distribution` |
| `category`, `flags` | most likely category with probability; flag probabilities |
| `fallback` | `triggered`, `floor`, `default_model`, `reason`. Triggers when no candidate clears the floor |
| `router` | `version`, `profiler`, `latency_ms`, `pool_hash` |
| `trace_id` | pass to `/outcome` and `/escalate` |

The response contains the card id (`card_id`), not the card's `provider` or `model`. To invoke the model, look the
card up in `cards/<card_id>.json`, use the MCP `list_models` tool, or `router.matcher.cards[card_id]` in Python.
See [INTEGRATIONS.md](INTEGRATIONS.md#mapping-a-pick-to-a-harness).

### `POST /escalate`

A model failed; get the next pick. The failure is evidence the task is harder, so the difficulty posterior shifts up.

Body: `{"request": <the original RouteRequest>, "response": <the RouteResponse you got>, "failed_model_id": "<id>"}`.
The server reuses the cached profile if it still has the `trace_id` (last 1024 routes), otherwise it re-profiles.

```sh
curl -s -X POST localhost:8765/escalate -H 'content-type: application/json' \
  -d '{"request": {...}, "response": {...}, "failed_model_id": "claude-sonnet-5.5"}'
```

The reply is a RouteResponse with a new `trace_id` and an `escalation` object (`parent_trace_id`,
`failed_models`, `prior_difficulty`, `posterior_difficulty`). Real output for a failed `claude-sonnet-5.5`
(difficulty mass moved up; no remaining candidate cleared the 0.55 floor, so the fallback picked the best available):

```json
{"choice": {"model_id": "codex-gpt-6-luna", "confidence": 0.4819, "decided_by": "fallback:best_available", ...},
 "escalation": {"parent_trace_id": "r_8f10ab11a5394f35a79c2032", "failed_models": ["claude-sonnet-5.5"], ...},
 "fallback": {"triggered": true, "floor": 0.55, "default_model": null,
              "reason": "no_candidate_above_floor;default_model_unavailable"}}
```

### `POST /outcome`

Log what happened. Required: `trace_id`, `model_id`, `success`.

| field | type |
|---|---|
| `trace_id`, `model_id` | string |
| `success` | boolean |
| `propensity` | number 0-1 or null |
| `signals` | `tests_passed`, `review_verdict`, `retries`, `user_override` |
| `quality` | number 0-1 |
| `actual_cost_usd`, `actual_latency_ms` | number >= 0 |
| `tokens` | `{"in": int, "out": int}` |

```sh
curl -s -X POST localhost:8765/outcome -H 'content-type: application/json' \
  -d '{"trace_id":"r_8f10ab11a5394f35a79c2032","model_id":"claude-sonnet-5.5","success":false,"signals":{"tests_passed":false},"actual_cost_usd":0.01,"actual_latency_ms":8000}'
# {"ok": true, "id": 1, "trace_id": "r_8f10ab11a5394f35a79c2032"}
```

Routes and outcomes are stored in SQLite (`--db`, else `$PANDA_ROUTER_DB`, else `data/cache/router_log.sqlite`).
Outcomes are logged for later calibration; the running router does not change its picks from them.

## CLI

`panda-router route` (same as `python -m panda_router.serve.cli route`) routes one task and prints the RouteResponse.
Exit code 2 and `{"error": ...}` on stderr for invalid input.

| flag | meaning |
|---|---|
| `--task TEXT` | **required** task text |
| `--context JSON` | `task.context` as JSON |
| `--kind-hint S` | `task.kind_hint` |
| `--pool a,b,c` | comma-separated card ids or names (default: all cards) |
| `--mode M` | `cheapest_above_threshold`, `max_utility`, `max_quality` |
| `--min-p P` | `preferences.min_p_success` |
| `--max-cost USD` | `constraints.max_cost_usd` |
| `--local-only` | only local (Ollama) cards |
| `--top-k N` | ranking length (default 3) |
| `--profile` | include the full TaskProfile |
| `--artifacts DIR` | ONNX profiler directory (default: heuristic profiler) |
| `--cards DIR` | cards directory (default `cards/`) |
| `--db PATH` | SQLite log path |
| `--no-log` | do not write the route to SQLite |

The CLI has no escalate or outcome command; use HTTP, MCP or Python.

Server flags (`panda-router-serve`): `--host`, `--port`, `--artifacts`, `--db`, `--cards`.

## Python

```python
from panda_router.serve.router import Router, load_profiler

router = Router(profiler=load_profiler("artifacts/panda-router-v3"), db_path="/tmp/router.sqlite")
req = {"task": {"text": "Add retry with backoff to the S3 uploader"},
       "pool": ["claude-sonnet-5.5", "claude-haiku-5.5", "ollama-qwen3-coder-30b"]}

resp = router.route(req)
card = router.matcher.cards[resp["choice"]["model_id"]]       # keyed by card id
print(resp["choice"]["model_id"], card["provider"], card["model"], resp["trace_id"])
# ollama-qwen3-coder-30b ollama qwen3-coder:30b r_a0ce9324f65046329452cf22

nxt = router.escalate(req, resp, resp["choice"]["model_id"])  # after a failure
router.record_outcome({"trace_id": nxt["trace_id"], "model_id": nxt["choice"]["model_id"], "success": True})
```

- `Router(profiler=None, matcher=None, db_path=None, cards_dir=None, log_routes=True)`. With no profiler it uses the
  heuristic profiler.
- `load_profiler(dir)` loads the ONNX profiler and raises if it cannot; `load_profiler(None)` returns the heuristic.
- `route(request)`, `escalate(request, response, failed_model_id)`, `record_outcome(outcome)`, `health()`.
- Invalid input raises `panda_router.serve.router.RequestError`. `router.matcher.cards` maps card id to the card dict
  (indexing with a pool alias that is not a card id raises `KeyError`; use `response["ranking"][i]["card_id"]`).

## MCP (stdio)

```sh
panda-router-mcp [--artifacts DIR] [--cards DIR] [--db PATH]
```

Env equivalents: `PANDA_ROUTER_ARTIFACTS`, `PANDA_ROUTER_CARDS`, `PANDA_ROUTER_DB`. If `--artifacts` is absent it uses
`artifacts/panda-router-v3` in the source checkout when present, otherwise the heuristic profiler (with a warning on
stderr). Newline-delimited JSON-RPC 2.0, protocol version `2025-06-18`, tools only. Logs go to stderr.

| tool | arguments | returns |
|---|---|---|
| `route_task` | `task_text` (required), `context`, `pool[]`, `mode`, `min_p_success`, `max_cost_usd`, `local_only`, `require[]`, `exclude[]`, `top_k` | text summary (`model=... P(success)=... difficulty=... category=... trace_id=...`) and the full RouteResponse as `structuredContent` |
| `escalate_task` | `trace_id`, `failed_model_id` (both required) | same as `route_task`, for the next pick. The `trace_id` must come from a route logged in the same database |
| `record_outcome` | `trace_id`, `model_id`, `success` (required); `cost_usd`, `latency_ms`, `notes` | `recorded outcome for <trace_id> (id=N)` |
| `list_models` | none | `{"models": [{id, provider, model, cost, local, description}]}` |

Tool-level failures (bad arguments, unknown `trace_id`) return `isError: true` with an `error: ...` message rather
than a protocol error. Real transcript from a stdio test (`route_task` then `escalate_task`, `record_outcome`):

```
model=codex-gpt-6-luna P(success)=0.992 difficulty=3 category=bugfix trace_id=r_f20d0184418c489d97080e0c
model=claude-haiku-5.5 P(success)=0.922 difficulty=4 category=bugfix trace_id=r_386d99ba50654d839b2de8d1
recorded outcome for r_f20d0184418c489d97080e0c (id=1)
```
