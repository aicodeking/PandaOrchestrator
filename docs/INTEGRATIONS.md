# Integrations

Panda Router only **chooses** a model. Your harness has to run it. Two integration styles:

- **MCP:** the agent calls `route_task` itself (Claude Code, Codex CLI, Cursor, OpenCode, SDK agents).
- **Direct:** your orchestrator calls the HTTP API, the CLI or the Python `Router` and dispatches the pick.

Tool and endpoint details are in [API.md](API.md).

## Verification status

| what | how it was checked |
|---|---|
| Panda Router MCP, HTTP, CLI, Python and shell snippets | **Run** against `artifacts/panda-router-v3` (Python 3.12, fresh venv) |
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
start the server from their own working directory. The profiler directory (`artifacts/panda-router-v3`) must exist
(see the README); without `--artifacts` and outside a checkout that has it, you get the weaker heuristic profiler.

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

Practical rule: **restrict `pool` to models your harness can actually run.** A Claude Code session cannot run
`ollama-*` or `codex-*` cards by itself, so pass `"pool": ["claude-opus-5.5", "claude-sonnet-5.5", "claude-haiku-5.5"]`.

## Claude Code

Register the MCP server (user scope so it applies in every project; `--` separates Claude's flags from the server's):

```sh
claude mcp add --scope user panda-router -- /ABS/PATH/PandaOrchestrator/.venv/bin/panda-router-mcp \
  --artifacts /ABS/PATH/PandaOrchestrator/artifacts/panda-router-v3
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
      "args": ["--artifacts", "/ABS/PATH/PandaOrchestrator/artifacts/panda-router-v3"],
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
Before delegating a subtask to a subagent, call `route_task` (panda-router MCP) with the subtask text,
`pool: ["claude-opus-5.5", "claude-sonnet-5.5", "claude-haiku-5.5"]` and `context` (repo_languages, files_in_scope).
Delegate with the model it returns: `claude-opus-5.5` -> opus, `claude-sonnet-5.5` -> sonnet,
`claude-haiku-5.5` -> haiku. Keep the `trace_id`.
If the subagent's result fails tests or review, call `escalate_task` with the `trace_id` and the failed model,
and retry with the new pick.
When the subtask is accepted or finally abandoned, call `record_outcome` with `trace_id`, `model_id`, `success`
(and `cost_usd` if known). Skip routing for trivial one-step edits.
```

### Subagent pattern

Make the main agent the dispatcher: it calls `route_task`, then starts a subagent with the matching model. Claude Code
subagents are Markdown files in `.claude/agents/` with YAML frontmatter, and the Task/Agent call can override the
model per invocation; define one generic worker and let the dispatcher choose its model. (Frontmatter field names
and model override behaviour were **not re-verified** for this version; check `/agents` in your Claude Code.)

## Codex CLI

Either run `codex mcp add` or edit `~/.codex/config.toml`. This is what `codex mcp add` (0.162.1) wrote:

```sh
codex mcp add panda-router --env PANDA_ROUTER_ARTIFACTS=/ABS/PATH/PandaOrchestrator/artifacts/panda-router-v3 \
  -- /ABS/PATH/PandaOrchestrator/.venv/bin/panda-router-mcp
```
```toml
[mcp_servers.panda-router]
command = "/ABS/PATH/PandaOrchestrator/.venv/bin/panda-router-mcp"

[mcp_servers.panda-router.env]
PANDA_ROUTER_ARTIFACTS = "/ABS/PATH/PandaOrchestrator/artifacts/panda-router-v3"
```

Put the same routing instructions as the CLAUDE.md snippet in `AGENTS.md`, with `pool` limited to `codex-*` cards
(for example `codex-gpt-6-luna`, `codex-gpt-5.6-terra`) and run the chosen model with `codex exec -m <card.model>`.

## Cursor

`.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global); project wins on name clashes. Per the Cursor docs
(not run here):

```json
{
  "mcpServers": {
    "panda-router": {
      "type": "stdio",
      "command": "/ABS/PATH/PandaOrchestrator/.venv/bin/panda-router-mcp",
      "args": ["--artifacts", "/ABS/PATH/PandaOrchestrator/artifacts/panda-router-v3"]
    }
  }
}
```

Cursor picks models in its own UI, so the router is advisory there: ask the agent to call `route_task` and tell you
which model to select, or use it from a rule file (`.cursor/rules`) with the CLAUDE.md text above.

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
                  "--artifacts", "/ABS/PATH/PandaOrchestrator/artifacts/panda-router-v3"],
      "enabled": true
    }
  }
}
```

`command` is a single array (executable plus arguments); environment variables go in an `environment` object.
Newer OpenCode docs describe a different "v2" layout (`mcp.servers`, `disabled` instead of `enabled`); use the layout
your version accepts. OpenCode models are `provider/model`, so an `openrouter` card becomes `openrouter/<card.model>`.

## Claude Agent SDK (Python)

Option A, MCP server (config shape per the SDK docs; not run here):

```python
from claude_agent_sdk import ClaudeAgentOptions, query

options = ClaudeAgentOptions(
    mcp_servers={"panda-router": {
        "command": "/ABS/PATH/PandaOrchestrator/.venv/bin/panda-router-mcp",
        "args": ["--artifacts", "/ABS/PATH/PandaOrchestrator/artifacts/panda-router-v3"],
    }},
    allowed_tools=["mcp__panda-router__*"],   # connecting a server does not grant permission to use its tools
)
async for msg in query(prompt="Route the subtasks, then ...", options=options):
    print(msg)
```

Option B, call `Router` directly and set the model per subtask (the Router part is tested; the `model=` option is
from SDK docs and was not run):

```python
from claude_agent_sdk import ClaudeAgentOptions, query
from panda_router.serve.router import Router, load_profiler

router = Router(profiler=load_profiler("artifacts/panda-router-v3"))
CLAUDE_POOL = ["claude-opus-5.5", "claude-sonnet-5.5", "claude-haiku-5.5"]

async def run_subtask(text: str):
    resp = router.route({"task": {"text": text}, "pool": CLAUDE_POOL})
    model = router.matcher.cards[resp["choice"]["model_id"]]["model"]      # e.g. "claude-sonnet-5-5"
    async for msg in query(prompt=text, options=ClaudeAgentOptions(model=model)):
        yield msg
    # then router.record_outcome({...}) from your own success check
```

## OpenAI Agents SDK

Over MCP (parameter names from tutorials; verify against your installed `openai-agents`):

```python
from agents import Agent, Runner
from agents.mcp import MCPServerStdio

async with MCPServerStdio(params={
    "command": "/ABS/PATH/PandaOrchestrator/.venv/bin/panda-router-mcp",
    "args": ["--artifacts", "/ABS/PATH/PandaOrchestrator/artifacts/panda-router-v3"],
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

router = Router(profiler=load_profiler("artifacts/panda-router-v3"))

def card_id(resp):  # the ranking entry of the chosen model (ranking[0] is not always the pick)
    return next(x["card_id"] for x in resp["ranking"] if x["model_id"] == resp["choice"]["model_id"])

LC = {"claude": "anthropic", "openrouter": "openrouter"}   # extend for the providers you use

def router_node(state):
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

Start `panda-router-serve --port 8765 --artifacts artifacts/panda-router-v3`, then loop:

```python
import requests

R = "http://127.0.0.1:8765"
def post(path, body): return requests.post(R + path, json=body, timeout=30).json()

def run_task(text, pool, max_attempts=3):
    req = {"task": {"text": text}, "pool": pool}
    resp = post("/route", req)
    for _ in range(max_attempts):
        model = resp["choice"]["model_id"]
        if model is None:
            break                                    # everything filtered out
        ok, cost = execute(model, text)              # your code: invoke the harness, run tests
        post("/outcome", {"trace_id": resp["trace_id"], "model_id": model, "success": ok, "actual_cost_usd": cost})
        if ok:
            return model
        resp = post("/escalate", {"request": req, "response": resp, "failed_model_id": model})
    return None
```

`execute` maps `model` to a command as in [Mapping a pick to a harness](#mapping-a-pick-to-a-harness). Remember that
the HTTP response does not contain `provider`; resolve it from `cards/`. The loop's HTTP calls match the ones run
with curl in [API.md](API.md#http).

## Shell scripts (CLI + jq)

```sh
TASK='Add retry with backoff to the S3 uploader'
OUT=$(panda-router route --artifacts artifacts/panda-router-v3 --db /tmp/router.sqlite --task "$TASK" \
        --pool claude-sonnet-5.5,claude-haiku-5.5 2>/dev/null)
echo "$OUT" | jq -r '[.choice.model_id, .trace_id, .difficulty.level] | @tsv'
# claude-haiku-5.5	r_175ec83aaf7841beaeb9a986	2
MODEL=$(echo "$OUT" | jq -r '.choice.model_id')
CARD=$(echo "$OUT" | jq -r '.choice.model_id as $m | .ranking[] | select(.model_id == $m) | .card_id')
jq -r '.model' "cards/$CARD.json"      # claude-haiku-5-5 -> pass to: claude -p --model <that>
```

The ONNX runtime loads on every CLI call, so a script that routes many tasks should use the HTTP server instead. The
CLI exits 2 with `{"error": ...}` on stderr when the pool resolves to nothing, so check `$?`.
