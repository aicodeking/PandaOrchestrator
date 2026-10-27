# How to integrate Panda Router for the best results

Panda Router picks a model. It does not run it or check the answer. Most of the measured gain comes from what
your orchestrator does around the pick: verify the result, and on a failure ask for the next model.

Numbers below are from [eval_reports/v4/REPORT.md](../eval_reports/v4/REPORT.md) (v4.2): 150 held-out real tasks,
each attempted by nine models and graded pass/fail by an LLM judge. Nothing was tuned on them.

| strategy (9-model pool) | success / 100 | $ / 100 tasks |
|---|---:|---:|
| single pick, `cheapest_above_threshold` | 74.0 | 0.74 |
| single pick, `max_utility` (default) | 77.3 | 0.99 |
| single pick, `max_quality` | 82.0 | 1.20 |
| always gpt-6.1-sol (best single model) | 79.3 | 1.11 |
| **follow `escalation_ladder`, up to 2 attempts (1 retry)** | **88.7** | **0.88** |
| follow `escalation_ladder`, up to 3 attempts (2 retries) | 92.0 | 1.23 |
| oracle (cheapest model that passed) | 94.0 | 0.56 |

The ladder rows treat the judge's verdict as the failure signal. In production your tests or reviewer play that role,
and the result is only as good as that signal. A single pick tops out around 77-82 because the router cannot tell
strong models apart per task; a verified retry does.

## 1. The loop

```
route  ->  run the opener  ->  verify  ->  pass? -> POST /outcome(success) -> done
                                   |
                                   +- fail -> POST /outcome(failure) -> POST /escalate -> run choice -> verify -> ...
                                              (at most 2 retries, then hand to a human)
```

1. `POST /route`. Read `escalation_ladder`: models in the order to try (cheap-but-safe first). The evaluated
   strategy starts at `escalation_ladder[0]`, not at `choice`. They are often the same model, but not always; see
   [Pitfalls](#pitfalls).
2. Run that model with your harness ([INTEGRATIONS.md](INTEGRATIONS.md#mapping-a-pick-to-a-harness)).
3. Verify (section 5). No check, no loop: use `max_quality` instead.
4. On failure, `POST /escalate` with the original request, the response you hold, and the model that failed. It
   follows the ladder in that response (`decided_by: "escalation_ladder"`), drops models that already failed, and
   shifts the difficulty estimate up. Use the new response's `choice.model_id` and `trace_id`.
5. Repeat up to 2 retries.
6. `POST /outcome` for every attempt, with `success`, cost and latency.

### Python (stdlib only)

Run against a local server (`panda-router-serve --port 8765`). With a stub `run_and_verify` that fails the first
model, this ran `claude-haiku-5.5` (fail) then `claude-sonnet-5.5` (pass):

```python
import json
import time
import urllib.request

ROUTER = "http://127.0.0.1:8765"
POOL = ["claude-opus-5.5", "claude-sonnet-5.5", "claude-haiku-5.5"]   # only models you can actually run


def post(path, body):
    req = urllib.request.Request(ROUTER + path, json.dumps(body).encode(), {"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def run_and_verify(model_id, text):
    """YOUR code: run `model_id` on `text`, then check the result (tests, lint, reviewer, LLM judge).
    Return {"ok": bool, "cost_usd": float, "output": str}."""
    raise NotImplementedError


def solve(text, context=None, mode="max_utility", max_retries=2):
    request = {"task": {"text": text, "context": context or {}}, "pool": POOL, "preferences": {"mode": mode}}
    response = post("/route", request)
    ladder = response.get("escalation_ladder") or []
    model = ladder[0]["model_id"] if ladder else response["choice"]["model_id"]   # cheap-but-safe opener
    for attempt in range(max_retries + 1):
        if model is None:
            return None                                   # everything was filtered out
        t0 = time.monotonic()
        result = run_and_verify(model, text)
        post("/outcome", {"trace_id": response["trace_id"], "model_id": model, "success": result["ok"],
                          "actual_cost_usd": result.get("cost_usd"),
                          "actual_latency_ms": (time.monotonic() - t0) * 1000,
                          "signals": {"retries": attempt}})
        if result["ok"]:
            return result["output"]
        if attempt < max_retries:
            response = post("/escalate", {"request": request, "response": response, "failed_model_id": model})
            model = response["choice"]["model_id"]        # follows the ladder; now a stronger pick
    return None                                           # still failing: hand to a human
```

### Shell (curl + jq)

Same loop; `run_and_verify` must exit 0 only on a pass. Run with a stub that rejects `claude-haiku-5.5`, it printed
`done by claude-sonnet-5.5`; with a stub that always fails it tried haiku, sonnet, opus and exited 1.

```sh
#!/bin/sh
# usage: ./loop.sh "task text"     needs: curl, jq, a running panda-router-serve
ROUTER=${ROUTER:-http://127.0.0.1:8765}
TASK=$1
POOL='["claude-opus-5.5","claude-sonnet-5.5","claude-haiku-5.5"]'

run_and_verify() {   # YOUR code: $1 = model_id, $2 = task. Exit 0 only if the result passes your checks.
  echo "would run $1" >&2; return 1
}

REQ=$(jq -n --arg t "$TASK" --argjson pool "$POOL" '{task:{text:$t}, pool:$pool}')
RESP=$(curl -s -X POST "$ROUTER/route" -H 'content-type: application/json' -d "$REQ")
MODEL=$(echo "$RESP" | jq -r '.escalation_ladder[0].model_id // .choice.model_id')

for ATTEMPT in 0 1 2; do
  [ "$MODEL" = null ] && break
  if run_and_verify "$MODEL" "$TASK"; then OK=true; else OK=false; fi
  curl -s -X POST "$ROUTER/outcome" -H 'content-type: application/json' \
    -d "$(jq -n --arg id "$(echo "$RESP" | jq -r .trace_id)" --arg m "$MODEL" --argjson ok $OK \
          --argjson n $ATTEMPT '{trace_id:$id, model_id:$m, success:$ok, signals:{retries:$n}}')" >/dev/null
  [ "$OK" = true ] && { echo "done by $MODEL"; exit 0; }
  RESP=$(curl -s -X POST "$ROUTER/escalate" -H 'content-type: application/json' \
    -d "$(jq -n --argjson req "$REQ" --argjson resp "$RESP" --arg m "$MODEL" \
          '{request:$req, response:$resp, failed_model_id:$m}')")
  MODEL=$(echo "$RESP" | jq -r '.choice.model_id')
done
echo "failed after retries" >&2; exit 1
```

### MCP (agent-driven)

When the agent itself calls the tools, put the loop in its instructions. This is the CLAUDE.md / `AGENTS.md`
snippet; the tool round trip (`route_task` -> `escalate_task` -> `record_outcome`) was run over stdio:

```markdown
## Model routing
Before delegating a subtask, call `route_task` (panda-router MCP) with the subtask text,
`pool: ["claude-opus-5.5", "claude-sonnet-5.5", "claude-haiku-5.5"]` and `context` (repo_languages, files_in_scope).
Start with the first model in the result's `escalation_ladder` (in structuredContent); if you cannot see it, use
the model named in the text. Keep the `trace_id`.
Verify the subtask's result: run the tests/lint/typecheck, or have a reviewer check it against the acceptance criteria.
If it fails, call `escalate_task` with the latest `trace_id` and the model that failed, then run the model it
returns. Allow at most 2 retries, then report the failure instead of looping.
After every attempt call `record_outcome` with that attempt's `trace_id`, `model_id`, `success` and `cost_usd`.
Skip routing for trivial one-step edits.
```

Over MCP, `escalate_task` needs the `trace_id` to be in the router's database (the default setup logs every route).
The `route_task` text line shows only the `choice`; the ladder is in the structured result.

## 2. Choosing a mode

| mode | picks | use when | measured single-shot (9 models) |
|---|---|---|---|
| `max_utility` (default) | best trade of P(success) against expected cost | general use | 77.3 @ $0.99 |
| `max_quality` | highest `p_success_lower`; models within 0.01 count as tied and the cheaper wins | a failure is expensive and you have no verifier | 82.0 @ $1.20 |
| `cheapest_above_threshold` | lowest expected cost among models whose `p_success_lower` >= `min_p_success` | bulk easy work with a verifier behind it | 74.0 @ $0.74 |

Expected cost includes failure: `cost + (1 - P) * (cost of the next-best model + $0.02)`. So a $0 or tiny model
does not win just by being cheap. A $0 / local model can only win if its lower bound is within 0.05 of the best paid
model's.

**`min_p_success` only affects `cheapest_above_threshold`.** The default is 0.5. Calibrated P is a strict-grading
pass rate and rarely exceeds about 0.65 for any model (the best model on "train a model" has a lower bound of
0.648), so a threshold of 0.75 usually has no qualifying model. The mode then returns the `max_quality` pick and
sets `decided_by: "policy:cheapest_above_threshold:relaxed"`. Real run, 3-model Claude pool, same task:

| mode, `min_p_success` | pick | `decided_by` |
|---|---|---|
| `cheapest_above_threshold`, 0.75 | claude-sonnet-5.5 (lower 0.631) | `policy:cheapest_above_threshold:relaxed` |
| `cheapest_above_threshold`, 0.5 | claude-haiku-5.5 (lower 0.572, $0.0002) | `policy:cheapest_above_threshold` |
| `max_utility` / `max_quality` | claude-sonnet-5.5 | `policy:max_utility` / `policy:max_quality` |

Use about 0.5 for cost-aware routing. Use 0.75 or higher only if you want "the safest model, always".
`:relaxed` is a signal, not an error.

`decided_by` may also end in `:equal_p_cheaper`: a cheaper model had nearly the same calibrated P (within 0.05, lower
bound not more than 0.05 below), so it replaced the pick. Full semantics: [API.md](API.md#modes).

## 3. Pool hygiene

- **Pass only models you can run.** The default pool is all 65 cards, including `openrouter-*` and `ollama-*` ones.
  If you have no OpenRouter key the router will happily pick `openrouter-gpt-6.1-sol` (for "What does HTTP 418
  mean?" in `max_utility` it did).
- Local models: pass only the ones you have pulled (`ollama list`). Ollama cards are tagged `not-installed`;
  `ollama pull` first or keep them out of `pool`. To drop a model for one request without editing the pool, use
  `constraints.exclude`.
- Subscription harnesses (Claude Code, Codex): include a card only while its quota lasts; drop it from `pool` when
  you hit a limit.
- Aliases are fine: `claude/sonnet-5-5`, `gpt-oss:20b`, `deepseek/deepseek-v4-flash`. Your string comes back as
  `model_id` and `card_id` shows the matched card. Unknown names appear in `filtered_out` as `unknown_model`:
  check it, a typo silently shrinks your pool.
- Keep cards current: prices, context limits, and a new model release. A card is one JSON file
  ([cards/README.md](../cards/README.md)); the server reloads it without a restart.
- `supersedes`: a newer card replaces an older one only when it costs the same or less for the task
  (`filtered_out`: `superseded_by:<id>`). Do not put both in `pool` expecting both to compete.
- A bigger pool is not a better pool for retries. The ladder needs at least two models with different strengths.

## 4. Give it context, and write good tasks

The profiler reads the task text plus a context line, so both matter.

| `task.context` field | effect |
|---|---|
| `repo_languages` | profiler input |
| `files_in_scope` | profiler input; high values raise `multi_file` and difficulty |
| `estimated_input_tokens` | profiler input, the cost estimate, and the context-window filter (default: text length / 4 + 500) |
| `has_images` | hard filter: only vision-capable models |
| `requires_tools` | hard filter: only tool-capable models |

Constraints do the same job as hard filters: `require: ["tools" | "vision" | "json_mode" | "web"]`.

Write the task like a ticket: scope (which files or module), the expected behaviour, and acceptance criteria
("`pytest tests/test_queue.py` passes"). Text over 6,000 characters is cut to its first and last 3,000, so put the
instruction at the start or end, not the middle.

**Vague requests are rated harder on purpose.** "a model trainer" gets difficulty about 5, not 1.5, and goes to a
paid model, because a short, ambiguous request can hide a lot of work. If your tasks are short but well specified,
add the specifics; if they are genuinely open-ended, the higher rating is correct. This is deliberate
(`vagueness` and `decision_level` in `difficulty`).

## 5. Verify, per task type

The ladder is only as good as your failure signal.

| task type | verification | notes |
|---|---|---|
| code change, bugfix | run the tests; add lint and typecheck | strongest signal; use the exit codes |
| refactor | existing tests plus a diff-size or API-surface check | tests that already pass prove behaviour kept |
| code review, writing, summaries | a cheap LLM judge with a rubric | judge with a different model family than the one that answered |
| data analysis | re-run the query/script and compare with a known answer or a second method | |
| no signal available | skip the ladder; use `max_quality` | a retry you cannot trigger buys nothing |

The v4 evaluation judge listed criteria for each task, then passed an answer only if every critical criterion was
met, at most one minor one was missed, and it had no material factual, math or code error; truncated, evasive or
placeholder answers failed (`JUDGE_PROMPT` in `panda_router/outcomes/grade.py`). Copy that shape. Those judges agreed
with a neutral reference at kappa 0.70-0.85, so expect some noise, and do not retry more than twice on a judge alone.

## 6. Send outcomes

Always call `POST /outcome` (or MCP `record_outcome`), for failures too. Every route and outcome is stored in SQLite
(`--db`, `$PANDA_ROUTER_DB`, or `data/cache/router_log.sqlite`), joined by `trace_id`, with the full request and
response JSON.

What it is for, honestly:

- The running router does **not** change its picks from outcomes. Nothing is learned online.
- The log is the raw material for refitting. The shipped model cards and the success head were fitted from graded
  attempt data ([data/outcomes/REPORT_v4_attempts.md](../data/outcomes/REPORT_v4_attempts.md)): task text, model,
  pass/fail. To refit on your own data, convert your logged routes and outcomes to the `success_cells.jsonl` shape
  (`task_id, split, text, card_id, pass, judge`) and rerun `scripts/outcomes/build_attempts.py` (card thetas) and
  `scripts/outcomes/train_success_head.py` (success head). No script reads the SQLite log directly yet; that
  conversion is yours to write.
- Useful fields: `success`, `actual_cost_usd`, `actual_latency_ms`, `signals.tests_passed`,
  `signals.review_verdict`, `signals.retries`, `tokens`. Cost and latency let you check `est_cost_usd` against
  reality.

## 7. Cost control

- `constraints.max_cost_usd`: models whose estimated cost for this task is higher are filtered out
  (`filtered_out` reason `constraint:max_cost_usd`). `max_latency_ms` works the same way.
- `constraints.local_only: true`: only local (Ollama) cards. If none are in the pool, `choice.model_id` is `null`
  and `decided_by` is `none:all_filtered`; handle that case.
- `constraints.exclude: [ids]`: never use these.
- Read `ranking[].est_cost_usd` (this call), `expected_cost_usd` (including the failure term) and
  `est_cost_to_success_usd`. They are estimates from card prices and the predicted output length, not bills. The
  v4 evaluation's own $ figures use the same estimates.
- Cheap models first, strong model last is what the ladder already does; a retry costs more only when the first
  attempt fails.

## Pitfalls

- **Models you cannot run.** The default pool includes cards for services you may not have. Always pass `pool`.
- **Strict `min_p_success`.** 0.75 or above makes `cheapest_above_threshold` fall back to the safest, priciest pick
  (`:relaxed`). Use about 0.5.
- **Ignoring the ladder.** Without a verified retry you get the single-pick numbers (74-82), not 88.7 / 92.0.
- **Escalation never steps down.** After a failure, `/escalate` only offers models at least as strong (by card
  skill) as the strongest one that failed: the next stronger ladder rung (`decided_by: escalation_ladder`), else the
  safest stronger model (`escalation:stronger`), else the strongest model left (`escalation:strongest_left`). You
  can start from `choice` or from `escalation_ladder[0]`. Measured on the 150 held-out tasks: starting at
  `escalation_ladder[0]` gives 88.7 within 2 attempts at $0.88/100 (cheapest); starting at `choice`
  (`max_utility`) gives 90.7 within 2 at $1.68/100 and 92.7 within 3.
- **Keep a strong model in the pool** and cap retries at 2: with a small pool, the strongest model can be reached
  quickly, after which there is nothing left to escalate to.
- **Not sending outcomes.** The log stays empty and you cannot check the router against your own results.
- **Trivial tasks show low P.** `p_success` is 0.4-0.6 even for "What does HTTP status 418 mean?" or "Rename a
  variable", because the outcome data has few trivial, well-specified tasks. Treat absolute P on trivial tasks as a
  strict lower estimate; compare P between models, not against a threshold. The policy handles it by treating nearly
  equal P as a tie that goes to the cheaper model.
- **`p_success` is not the odds your check passes.** It is calibrated to an LLM judge's strict grading on our
  held-out tasks. Your tests may be easier or harder.
- **The CLI in a loop.** It loads the ONNX model on every call (about 3.7 s wall time here, vs about 10-25 ms for a
  route on the server), and it has no escalate or outcome command. Use the HTTP server or MCP for loops.
- **Exposed server.** It has no authentication and binds to 127.0.0.1. Keep it there.

See also: [API.md](API.md) for every field, [INTEGRATIONS.md](INTEGRATIONS.md) for harness setup,
[README](../README.md#results) for the full results table.
