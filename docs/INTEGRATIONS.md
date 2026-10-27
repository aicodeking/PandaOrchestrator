# Integrations

Panda Router only **chooses** a model. Your harness has to run it. Two integration styles:

- **MCP:** the agent calls `route_task` itself (Claude Code, Codex CLI, Cursor, OpenCode, SDK agents).
- **Direct:** your orchestrator calls the HTTP API, the CLI or the Python `Router` and dispatches the pick.

Tool and endpoint details are in [API.md](API.md). Whichever style you use, the best results come from the loop
route -> run -> verify -> escalate on failure -> report the outcome; see
[BEST_RESULTS.md](BEST_RESULTS.md) for the loop, the modes and the pitfalls.

## Verification status

| what | how it was checked |
|---|---|
| Panda Router MCP (stdio round trip: route, escalate, outcome), HTTP, CLI, Python and shell snippets, and the loops in [BEST_RESULTS.md](BEST_RESULTS.md) | **Run** against `artifacts/panda-router-v4` (Python 3.12), 2026-10-27. The loops ran with a stub in place of the model call |
| Claude Code 2.1.310: `claude mcp add --scope project ...` | **Run**; it wrote the `.mcp.json` shown below. Project-scope servers then show "Pending approval" until you approve them in a session, so tool calls from a live Claude session were **not** run |
| Codex CLI 0.162.1: `codex mcp add` | **Run** with a temporary `CODEX_HOME`; it wrote the TOML shown. `codex mcp list` lists the server. A live Codex session calling the tools was not run |
| OpenCode 1.19.0: `opencode.json` `mcp` entry | **Run**; `opencode mcp list` reported the server `connected`. A model calling the tools was not run |
| Cursor `.cursor/mcp.json` | Docs only ([cursor.com/docs/mcp](https://cursor.com/docs/mcp)), checked 2026-10-26. Cursor not installed here. **Unverified by execution** |
| Claude Agent SDK (Python) `mcp_servers` | Docs only ([code.claude.com agent-sdk MCP page](https://code.claude.com/docs/en/agent-sdk/mcp) and mirrors). SDK not installed here. **Unverified by execution** |
| OpenAI Agents SDK `MCPServerStdio` | Third-party tutorials only; the official page was not retrieved. **Unverified by execution**, check parameter names against your installed version |
| LangChain `langchain-mcp-adapters` | Docs only ([docs.langchain.com/oss/python/langchain/mcp](https://docs.langchain.com/oss/python/langchain/mcp)). **Unverified by execution** |
| Claude Code subagent frontmatter, `claude --model` / `codex exec -m` / `opencode run -m` flags | `--model`/`-m` flags confirmed in each CLI's `--help`. Subagent file format **not re-checked** |

Config formats change often. If a snippet fails, trust the client's current docs over this page.

## Install once

```sh
git clone https://github.com/AICodeKing/PandaOrchestrator.git && cd PandaOrchestrator
python3.12 -m venv .venv && . .venv/bin/activate && pip install -e .
which panda-router-mcp   # use this absolute path in the configs below
```

In the configs below, replace `/ABS/PATH/PandaOrchestrator` with your checkout. Use absolute paths: MCP clients
start the server from their own working directory. The profiler directory (`artifacts/panda-router-v4`, with the
success head `success_head.json` inside it) must exist; without `--artifacts` and outside a checkout that has it, you
get the weaker heuristic profiler.

## Mapping a pick to a harness

Every response gives `choice.model_id` (your string) and `ranking[i].card_id`. The card holds `provider` and
`model`, which tell you how to invoke it. Over MCP, `list_models` returns `id`, `provider`, `model`. Over HTTP read
`cards/<card_id>.json`. In Python use `router.matcher.cards[card_id]`.

| card `provider` | card `model` example | how to run it |
|---|---|---|
| `claude` | `claude-sonnet-5-5` | `claude -p --model claude-sonnet-5-5 "<task>"` (Claude Code), or the Anthropic API model id |
| `codex` | `gpt-6-luna` | `codex exec -m gpt-6-luna "<task>"` |
| `ollama` | `qwen3-coder:30b` | `ollama run qwen3-coder:30b "<task>"` (after `ollama pull`); OpenCode/other tools via Ollama's API |
| `openrouter` | `deepseek/deepseek-v4-flash` | the slug is the `model` field of `POST https://openrouter.ai/api/v1/chat/completions`; in OpenCode use `openrouter/<slug>` (`opencode run -m openrouter/deepseek/deepseek-v4-flash "<task>"`, `-m` takes `provider/model`) |
| `glm`, `grok`, `kimi` | `glm-5-turbo`, `grok-4.6`, `kimi-k3` | the vendor's API model name. How to point a coding CLI at these vendors depends on the vendor's compatible endpoint and is not covered or verified here |

`--model`, `-m` and `ollama run` syntax were taken from each tool's `--help` (Claude Code 2.1.310, Codex 0.162.1,
OpenCode 1.19.0, Ollama 0.40.6). The `claude` and `codex` rows assume you are signed in to those tools.

Practical rule: **restrict `pool` to models your harness can actually run.** The default pool is all 65 cards,
including `openrouter-*` ones that need a key and `ollama-*` ones that need a pull. A Claude Code session cannot run
`ollama-*` or `codex-*` cards by itself, so pass `"pool": ["claude-opus-5.5", "claude-sonnet-5.5", "claude-haiku-5.5"]`
([pool hygiene](BEST_RESULTS.md#3-pool-hygiene)).

## Claude Code

Register the MCP server (user scope so it applies in every project; `--` separates Claude's flags from the server's):

```sh
claude mcp add --scope user panda-router -- /ABS/PATH/PandaOrchestrator/.venv/bin/panda-router-mcp \
  --artifacts /ABS/PATH/PandaOrchestrator/artifacts/panda-router-v4
claude mcp list
```

`--scope project` writes a `.mcp.json` like this (this is the actual output of `claude mcp add` 2.1.310) and asks
each user to approve it on first use:

```json
{
  "mcpServers": {
    "panda-router": {
      "type": "stdio",
      "command": "/ABS/PATH/PandaOrchestrator/.venv/bin/panda-router-mcp",
      "args": ["--artifacts", "/ABS/PATH/PandaOrchestrator/artifacts/panda-router-v4"],
      "env": {}
    }
  }
}
```

The tools appear as `mcp__panda-router__route_task`, `mcp__panda-router__escalate_task`,
`mcp__panda-router__record_outcome`, `mcp__panda-router__list_models`.

### CLAUDE.md snippet

```markdown
## Model routing
Before delegating a subtask, call `route_task` (panda-router MCP) with the subtask text,
`pool: ["claude-opus-5.5", "claude-sonnet-5.5", "claude-haiku-5.5"]` and `context` (repo_languages, files_in_scope).
Start with the first model in the result's `escalation_ladder` (in structuredContent); if you cannot see it, use
the model named in the text. Delegate with it: `claude-opus-5.5` -> opus, `claude-sonnet-5.5` -> sonnet,
`claude-haiku-5.5` -> haiku. Keep the `trace_id`.
Verify the subtask's result: run the tests/lint/typecheck, or have a reviewer check it against the acceptance criteria.
If it fails, call `escalate_task` with the latest `trace_id` and the model that failed, then retry with the model it
returns. Allow at most 2 retries, then report the failure instead of looping.
After every attempt call `record_outcome` with that attempt's `trace_id`, `model_id`, `success` and `cost_usd`.
Skip routing for trivial one-step edits.
```

The reasoning and the measured gain of the retry loop: [BEST_RESULTS.md](BEST_RESULTS.md#1-the-loop).

### Subagent pattern

Make the main agent the dispatcher: it calls `route_task`, then starts a subagent with the matching model. Claude Code
subagents are Markdown files in `.claude/agents/` with YAML frontmatter, and the Task/Agent call can override the
model per invocation; define one generic worker and let the dispatcher choose its model. (Frontmatter field names
and model override behaviour were **not re-verified** for this version; check `/agents` in your Claude Code.)
Have the dispatcher verify each subagent's result and follow the retry rules above; the loop is in
[BEST_RESULTS.md](BEST_RESULTS.md#mcp-agent-driven).

## Codex CLI

Either run `codex mcp add` or edit `~/.codex/config.toml`. This is what `codex mcp add` (0.162.1) wrote:

```sh
codex mcp add panda-router --env PANDA_ROUTER_ARTIFACTS=/ABS/PATH/PandaOrchestrator/artifacts/panda-router-v4 \
  -- /ABS/PATH/PandaOrchestrator/.venv/bin/panda-router-mcp
```
```toml
[mcp_servers.panda-router]
command = "/ABS/PATH/PandaOrchestrator/.venv/bin/panda-router-mcp"

[mcp_servers.panda-router.env]
PANDA_ROUTER_ARTIFACTS = "/ABS/PATH/PandaOrchestrator/artifacts/panda-router-v4"
```

Put the same routing instructions as the CLAUDE.md snippet in `AGENTS.md`, with `pool` limited to `codex-*` cards
(for example `codex-gpt-6-luna`, `codex-gpt-5.6-terra`) and run the chosen model with `codex exec -m <card.model>`.
Retry loop and verification: [BEST_RESULTS.md](BEST_RESULTS.md#1-the-loop).

## Cursor

`.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global); project wins on name clashes. Per the Cursor docs
(not run here):

```json
{
  "mcpServers": {
    "panda-router": {
      "type": "stdio",
      "command": "/ABS/PATH/PandaOrchestrator/.venv/bin/panda-router-mcp",
      "args": ["--artifacts", "/ABS/PATH/PandaOrchestrator/artifacts/panda-router-v4"]
    }
  }
}
```

Cursor picks models in its own UI, so the router is advisory there: ask the agent to call `route_task` and tell you
which model to select, or use it from a rule file (`.cursor/rules`) with the CLAUDE.md text above. Because Cursor cannot
re-run a model by itself, the escalate-on-failure part of [BEST_RESULTS.md](BEST_RESULTS.md) is manual there.

## OpenCode

`opencode.json` in the project root (or `~/.config/opencode/opencode.json`). `opencode mcp list` showed this server
as `connected` on OpenCode 1.19.0:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "panda-router": {
      "type": "local",
      "command": ["/ABS/PATH/PandaOrchestrator/.venv/bin/panda-router-mcp",
                  "--artifacts", "/ABS/PATH/PandaOrchestrator/artifacts/panda-router-v4"],
      "enabled": true
    }
  }
}
```

`command` is a single array (executable plus arguments); environment variables go in an `environment` object.
Newer OpenCode docs describe a different "v2" layout (`mcp.servers`, `disabled` instead of `enabled`); use the layout
your version accepts. OpenCode models are `provider/model`, so an `openrouter` card becomes `openrouter/<card.model>`.
Use the routing instructions and retry loop from [BEST_RESULTS.md](BEST_RESULTS.md#mcp-agent-driven) in your
`AGENTS.md`.

## Claude Agent SDK (Python)

Option A, MCP server (config shape per the SDK docs; not run here):

```python
from claude_agent_sdk import ClaudeAgentOptions, query

options = ClaudeAgentOptions(
    mcp_servers={"panda-router": {
        "command": "/ABS/PATH/PandaOrchestrator/.venv/bin/panda-router-mcp",
        "args": ["--artifacts", "/ABS/PATH/PandaOrchestrator/artifacts/panda-router-v4"],
    }},
    allowed_tools=["mcp__panda-router__*"],   # connecting a server does not grant permission to use its tools
)
async for msg in query(prompt="Route the subtasks, then ...", options=options):
    print(msg)
```

Option B, call `Router` directly and set the model per subtask (the Router part is tested; the `model=` option is
from SDK docs and was not run). Add the verify-and-escalate loop from [BEST_RESULTS.md](BEST_RESULTS.md#python-stdlib-only):

```python
from claude_agent_sdk import ClaudeAgentOptions, query
from panda_router.serve.router import Router, load_profiler

router = Router(profiler=load_profiler("artifacts/panda-router-v4"))
CLAUDE_POOL = ["claude-opus-5.5", "claude-sonnet-5.5", "claude-haiku-5.5"]

async def run_subtask(text: str):
    resp = router.route({"task": {"text": text}, "pool": CLAUDE_POOL})
    first = resp["escalation_ladder"][0]["model_id"]                        # cheap-but-safe opener
    model = router.matcher.cards[first]["model"]                            # e.g. "claude-haiku-5-5"
    async for msg in query(prompt=text, options=ClaudeAgentOptions(model=model)):
        yield msg
    # then verify, router.record_outcome({...}), and on failure router.escalate(req, resp, first)
```

## OpenAI Agents SDK

Over MCP (parameter names from tutorials; verify against your installed `openai-agents`):

```python
from agents import Agent, Runner
from agents.mcp import MCPServerStdio

async with MCPServerStdio(params={
    "command": "/ABS/PATH/PandaOrchestrator/.venv/bin/panda-router-mcp",
    "args": ["--artifacts", "/ABS/PATH/PandaOrchestrator/artifacts/panda-router-v4"],
}) as router_mcp:
    agent = Agent(name="Dispatcher", instructions="Call route_task before delegating; call record_outcome after.",
                  mcp_servers=[router_mcp])
    result = await Runner.run(agent, "Plan and implement ...")
```

Or as a plain function tool that calls the local `Router` (no MCP), returning only what the model needs:

```python
from agents import function_tool
# router and card_id(): as defined in the LangGraph example below

@function_tool
def route_task(task_text: str) -> str:
    r = router.route({"task": {"text": task_text}})
    c = router.matcher.cards[card_id(r)]
    return f'{c["provider"]}:{c["model"]} trace_id={r["trace_id"]}'
```

## LangGraph / LangChain

Use a router node that picks the chat model, then a worker node that invokes it. The Router part was run; the
`init_chat_model` mapping is yours to adapt.

```python
from langchain.chat_models import init_chat_model
from panda_router.serve.router import Router, load_profiler

router = Router(profiler=load_profiler("artifacts/panda-router-v4"))

def card_id(resp):  # the ranking entry of the chosen model (ranking[0] is not always the pick)
    return next(x["card_id"] for x in resp["ranking"] if x["model_id"] == resp["choice"]["model_id"])

LC = {"claude": "anthropic", "openrouter": "openrouter"}   # extend for the providers you use

def router_node(state):  # on a retry, call router.escalate(request, last_response, failed_model_id) instead
    r = router.route({"task": {"text": state["task"]}, "pool": state["pool"]})
    card = router.matcher.cards[card_id(r)]
    return {"trace_id": r["trace_id"], "card_id": card["id"], "provider": card["provider"], "model": card["model"]}

def worker_node(state):
    llm = init_chat_model(state["model"], model_provider=LC[state["provider"]])
    return {"answer": llm.invoke(state["task"]).content}
```

To expose the MCP tools to a LangChain agent instead, use `langchain-mcp-adapters`:
`MultiServerMCPClient({"panda-router": {"command": ..., "args": [...], "transport": "stdio"}})`, then
`await client.get_tools()` (per its docs; not run here).

## Any orchestrator over HTTP

Start `panda-router-serve --port 8765 --artifacts artifacts/panda-router-v4`, then use the stdlib loop in
[BEST_RESULTS.md](BEST_RESULTS.md#python-stdlib-only): `POST /route`, run `escalation_ladder[0]`, verify,
`POST /outcome`, and on a failure `POST /escalate` (up to 2 retries). That loop was run against a local server with a
stub in place of the model call. In short:

```python
resp = post("/route", req)
model = resp["escalation_ladder"][0]["model_id"]
for attempt in range(3):
    ok, cost = execute(model, text)           # your code: invoke the harness, run tests
    post("/outcome", {"trace_id": resp["trace_id"], "model_id": model, "success": ok, "actual_cost_usd": cost})
    if ok or attempt == 2:
        break
    resp = post("/escalate", {"request": req, "response": resp, "failed_model_id": model})
    model = resp["choice"]["model_id"]
```

`execute` maps `model` to a command as in [Mapping a pick to a harness](#mapping-a-pick-to-a-harness). Remember that
the HTTP response does not contain `provider`; resolve it from `cards/`. The loop's HTTP calls match the ones run
with curl in [API.md](API.md#http).

## Shell scripts (CLI + jq)

For a one-shot route (no retry), the CLI works:

```sh
TASK='Add retry with backoff to the S3 uploader'
OUT=$(panda-router route --artifacts artifacts/panda-router-v4 --db /tmp/router.sqlite --task "$TASK" \
        --pool claude-sonnet-5.5,claude-haiku-5.5 2>/dev/null)
echo "$OUT" | jq -r '[.escalation_ladder[0].model_id, .trace_id, .difficulty.level] | @tsv'
MODEL=$(echo "$OUT" | jq -r '.escalation_ladder[0].model_id')
CARD=$(echo "$OUT" | jq -r --arg m "$MODEL" '.ranking[] | select(.model_id == $m) | .card_id')
jq -r '.model' "cards/$CARD.json"      # claude-haiku-5-5 -> pass to: claude -p --model <that>
```

The ONNX runtime loads on every CLI call (about 3-4 s here), and the CLI has no escalate or outcome command. For a
retry loop use the HTTP server: the curl + jq loop is in [BEST_RESULTS.md](BEST_RESULTS.md#shell-curl--jq). The CLI
exits 2 with `{"error": ...}` on stderr when the pool resolves to nothing, so check `$?`.
