# Panda Router

A small local router that picks which LLM should handle a task.

A 31 MB ONNX task profiler (Ettin-32M, distilled from a 150M teacher) reads the task text and outputs a
category, a difficulty from 1 to 10, the skill levels it needs, and a few flags. A deterministic matcher then
scores about 65 model cards (Claude, Codex/GPT, Grok, GLM, Kimi, top OpenRouter models, Ollama library models)
by P(success), cost and latency, and picks one under a policy you choose. A route takes roughly 10-25 ms on a
CPU. Nothing leaves your machine.

```
            task text + optional context
                        |
                        v
        +-------------------------------+
        |  profiler (ONNX int8, 31 MB)  |   category, difficulty 1-10,
        |  Ettin-32M encoder + heads    |   skill levels, flags, token estimate
        +---------------+---------------+
                        |  TaskProfile
                        v
        +-------------------------------+      cards/*.json
        |  matcher (deterministic)      | <--  per-model skills, price,
        |  P(success), cost, latency    |      context, latency
        +---------------+---------------+
                        |  policy: cheapest_above_threshold | max_utility | max_quality
                        v
        chosen model + ranking + trace_id  ->  you run it  ->  /outcome  (or /escalate on failure)
```

Features: pool name aliases (your exact string is echoed back, `card_id` shows the match), newer versions
supersede older ones when they are not pricier, escalation after a failure, SQLite outcome logging, an HTTP
server, a CLI, a Python API and an MCP server.

> The router returns a model *name*. It does not call the model. See [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md)
> for how to turn the pick into `claude --model`, `codex -m`, `ollama run` or an OpenRouter slug.

## Quickstart

Requires Python 3.12+.

```sh
git clone https://github.com/AICodeKing/PandaOrchestrator.git
cd PandaOrchestrator
python3.12 -m venv .venv && . .venv/bin/activate
pip install -e .            # core: serving only (onnxruntime, transformers tokenizer, numpy, scipy, jsonschema; no torch)
pip install -e ".[train]"   # optional: torch and friends, only needed to retrain or export (see docs below)
```

The trained profiler ships in the repo at `artifacts/panda-router-v3/` (31 MB int8 ONNX `model.int8.onnx`,
`heads.json`, tokenizer files). The 128 MB fp32 export is not committed; the router only needs the int8 model.
Without `--artifacts` the CLI falls back to a keyword heuristic profiler, which works but is clearly weaker
(see [Results](#results)); the HTTP and MCP servers default to `artifacts/panda-router-v3` in a source
checkout. An explicitly given `--artifacts` directory that fails to load is an error, not a silent fallback.

**Route one task (CLI)**

```sh
panda-router route --artifacts artifacts/panda-router-v3 --no-log \
  --task 'Rename a variable in utils.py' \
  --pool claude/sonnet-5-5,claude-haiku-5.5,gpt-oss:20b --mode max_utility --top-k 3
```

`panda-router route` prints a RouteResponse as JSON. Add `--profile` to include the full TaskProfile,
`--context '{"repo_languages":["python"],"files_in_scope":2}'` for hints, `--local-only`, `--max-cost USD`,
`--min-p 0.8`. All flags are listed in [docs/API.md](docs/API.md#cli).

**Start the HTTP server**

```sh
panda-router-serve --port 8765 --artifacts artifacts/panda-router-v3
# [panda-router] listening on http://127.0.0.1:8765 (profiler=OnnxProfiler(panda-router-v3/model.int8.onnx), ...)
curl -s localhost:8765/health
```

**Start the MCP server (stdio)**

```sh
panda-router-mcp --artifacts artifacts/panda-router-v3
```

It speaks newline-delimited JSON-RPC on stdin/stdout and exposes `route_task`, `escalate_task`,
`record_outcome` and `list_models`. Clients normally launch it for you; see
[docs/INTEGRATIONS.md](docs/INTEGRATIONS.md). In a source checkout, `--artifacts` defaults to
`artifacts/panda-router-v3` when that directory exists.

## Example

```sh
curl -s -X POST localhost:8765/route -H 'content-type: application/json' -d '{
  "task": {"text": "Migrate our Express auth middleware to use JWT refresh tokens and update all call sites",
           "context": {"repo_languages": ["typescript"], "files_in_scope": 12}},
  "pool": ["claude-sonnet-5.5", "claude-haiku-5.5", "codex-gpt-6-luna", "ollama-qwen3-coder-30b"],
  "preferences": {"mode": "cheapest_above_threshold", "min_p_success": 0.8},
  "return_top_k": 2
}'
```

Real output (the `difficulty.distribution` array is shortened to two entries):

```json
{
  "choice": {"model_id": "claude-sonnet-5.5", "confidence": 0.8961,
             "decided_by": "policy:cheapest_above_threshold", "propensity": 1.0, "explored": false},
  "ranking": [
    {"model_id": "claude-sonnet-5.5", "card_id": "claude-sonnet-5.5", "p_success": 0.8961, "quality": 0.8367,
     "utility": 0.3586, "est_cost_usd": 0.026693, "est_cost_to_success_usd": 0.029788, "est_latency_ms": 31078.0},
    {"model_id": "codex-gpt-6-luna", "card_id": "codex-gpt-6-luna", "p_success": 0.7712, "quality": 0.731,
     "utility": 0.4488, "est_cost_usd": 0.001335, "est_cost_to_success_usd": 0.001731, "est_latency_ms": 34064.1}
  ],
  "filtered_out": [],
  "difficulty": {"level": 5, "expected": 5.685, "distribution": [0.013417, 0.025009, "..."]},
  "category": {"label": "implementation", "p": 0.7856},
  "flags": {"needs_tools": 0.1835, "needs_vision": 0.0057, "long_context": 0.0082, "needs_review": 0.8608,
            "ambiguous_spec": 0.9294, "multi_file": 0.9169, "needs_web": 0.0538},
  "fallback": {"triggered": false, "floor": 0.55, "default_model": "claude-opus-5.5"},
  "router": {"version": "panda-router-0.1.0", "profiler": "OnnxProfiler(panda-router-v3/model.int8.onnx)",
             "latency_ms": 22.67, "pool_hash": "..."},
  "trace_id": "r_8f10ab11a5394f35a79c2032"
}
```

The cheapest model that clears `min_p_success` (0.8) is `claude-sonnet-5.5`; `codex-gpt-6-luna` is cheaper but
only 0.77. If the pick fails, call `/escalate` with the failed model; the failure is treated as evidence that the
task is harder. Report the final result with `/outcome`. Details: [docs/API.md](docs/API.md).

## Results

### Real routed success (v3)

140 held-out real tasks (non-coding and small coding, single-turn), each actually attempted by five OpenRouter
models (qwen3.8-flash, deepseek-v4.1-flash, minimax-m3.1-flash, gemini-3.8-flash, gpt-6.1-sol) and graded
pass/fail by DeepSeek V4.1 Flash (kappa 0.85 against a Kimi K3.1 Pro reference). The router picks from those
five; we count how often its pick actually passed. Report: [data/outcomes/REPORT_attempts.md](data/outcomes/REPORT_attempts.md).

| policy | success / 100 | $ / 100 tasks |
|---|---:|---:|
| always cheapest (qwen3.8-flash) | 47.1 | 0.064 |
| v2, old default (`cheapest_above_threshold`) | 50.0 | 0.095 |
| v3, `cheapest_above_threshold` | 51.4 | 0.142 |
| **v3, `max_utility` (new default)** | **67.9** | **0.156** |
| always strongest (gpt-6.1-sol) | 78.6 | 1.061 |
| oracle (cheapest model that passed) | 90.0 | 0.192 |

The default mode is now `max_utility`: it gets 86% of always-strongest's successes at 15% of its cost. The gap to
the oracle is still large; better model cards are the main lever (see Limitations).

### Profiler quality

Evaluated on 359 real tasks (the gold set) that were never trained on, labelled by Codex + DeepSeek V4.1 Flash.
Full tables: [eval_reports/compare_v3.md](eval_reports/compare_v3.md); release notes: [RESULTS.md](RESULTS.md).

| profiler | gold category acc | gold difficulty MAE / rho | gold flags AUROC | attempt-IRT rho | SWE held-out rho | hard-task pass |
|---|---:|---:|---:|---:|---:|---:|
| v1 | 0.624 | 0.900 / 0.675 | 0.885 | 0.178 | 0.025 | 0.80 |
| v2 | 0.641 | 0.897 / 0.705 | 0.886 | 0.115 | **0.119** | 0.85 |
| **v3 (shipped)** | **0.688** | **0.825 / 0.747** | **0.901** | **0.212** | 0.081 | 0.85 |

- v3 is a direct Ettin-32M trained on 8,247 tasks (every row labelled by at least two teachers, DeepSeek V4.1
  Flash on all of them) with real-outcome difficulty from SWE-bench and from the attempt-and-grade runs as an
  auxiliary target (weight 0.3). 31 MB int8.
- *attempt-IRT rho*: rank correlation between predicted difficulty and difficulty fitted from the real
  attempts above. *SWE held-out rho*: the same against SWE-bench item difficulty on repos never trained on; v3 is
  lower here than v2 (0.08 vs 0.12, both weak).
- Latency: v1-v3 share one 32M architecture; on an idle host the profiler runs at about 10 ms p50 / 19 ms p95
  (batch 1, CPU, int8).

## Model cards

Each routable model is one JSON file in [cards/](cards/), validated by
[schemas/model_card.schema.json](schemas/model_card.schema.json). To add a model, copy the closest card, set
`id` (same as the file name), `provider`, `model`, `cost`, `limits`, `skills` and `latency`, and run
`pytest tests/test_matcher.py`. The router reloads changed cards without a restart.

- **Aliases:** `pool` entries may be card ids, the card's `model` string (`gpt-oss:20b`, `deepseek/deepseek-v4-flash`),
  or a loose spelling (`claude/sonnet-5-5`). The response echoes your string as `model_id` and sets `card_id`.
  Ambiguous or unknown names come back in `filtered_out` as `unknown_model`.
- **Supersedes:** a card can list older versions in `supersedes`. The older one is dropped only if the newer one
  costs the same or less for the task.
- **Free OpenRouter tiers** live in `cards/optional/` and are not in the default pool.

Full guide: [cards/README.md](cards/README.md) (also [docs/CARDS.md](docs/CARDS.md)).

## Repo layout

```
panda_router/     serve/ (Router, HTTP server, CLI), mcp/ (stdio MCP server), matcher/, model/ (net, ONNX profiler),
                  train/, datagen/, outcomes/ (IRT fit), eval/, heuristic.py
cards/            one JSON per model (+ optional/ for free tiers)
schemas/          JSON Schemas for requests, responses, outcomes, cards; CONTRACTS.md; taxonomy.json
scripts/          datagen/, train/, eval/, outcomes/ entry points
data/             training data, gold set, outcome fits (STATS.md, gold/README.md, outcomes/REPORT.md)
eval_reports/     comparison tables and per-model reports
docs/             API.md, INTEGRATIONS.md, CARDS.md
tests/            pytest suite
RESULTS.md        v2 release decision and ablations
PLAN.md           design plan
```

## Training and reproduction

Install the `[train]` extra, then follow [panda_router/train/README.md](panda_router/train/README.md) (teacher,
distillation, soup, calibration, ONNX export, latency bench, v2 outcome anchors).
Data construction and statistics: [data/STATS.md](data/STATS.md); gold set: [data/gold/README.md](data/gold/README.md);
outcome calibration: [data/outcomes/REPORT.md](data/outcomes/REPORT.md). Run the tests with `pip install -e ".[dev]"`
and `pytest`.

## Data, licences and attribution

Code and the released model weights are MIT ([LICENSE](LICENSE)). Training data, evaluation data and base model:

| source | used for | licence |
|---|---|---|
| [SWE-rebench](https://huggingface.co/datasets/nebius/SWE-rebench) (Nebius) | task text (`problem_statement`), gold set, outcome anchors | CC-BY-4.0 |
| [SWE-smith](https://huggingface.co/datasets/SWE-bench/SWE-smith) | task text | MIT |
| [WildChat-1M](https://huggingface.co/datasets/allenai/WildChat-1M) (AI2) | first user turns of English chats | ODC-BY |
| [SWE-bench](https://github.com/SWE-bench/SWE-bench) (and Verified, Lite, Multilingual) | issue text for outcome-difficulty tasks | MIT |
| [swe-bench/experiments](https://github.com/swe-bench/experiments) | per-instance resolved lists, used as facts for the IRT fit; raw files are not redistributed | no licence file |
| [Ettin encoders](https://huggingface.co/jhu-clsp/ettin-encoder-32m) (JHU CLSP) | backbone | MIT |

Teacher labels were produced by LLMs (see Limitations). Repo code inside SWE-rebench keeps its own licence.
More detail per source: [data/gold/README.md](data/gold/README.md) and [data/outcomes/REPORT.md](data/outcomes/REPORT.md).
