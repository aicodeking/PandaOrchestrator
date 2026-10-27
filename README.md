# Panda Router

A small local router that picks which LLM should handle a task.

A 31 MB ONNX task profiler (Ettin-32M, distilled from a 150M teacher) reads the task text and outputs a
category, a difficulty from 1 to 10, the skill levels it needs, and a few flags. A learned success head turns that
profile into a calibrated P(success) for each model it was trained on; the other cards use a conservative prior.
A deterministic policy then scores about 65 model cards (Claude, Codex/GPT, Grok, GLM, Kimi, top OpenRouter models,
Ollama library models) by P(success), expected cost (failures included) and latency, and picks one under the mode you
choose. It also returns an `escalation_ladder`: the models to try, in order, if you verify the result and it fails.
A route takes roughly 10-25 ms on a CPU. Nothing leaves your machine.

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
        +-------------------------------+      cards/*.json + success head
        |  matcher (deterministic)      | <--  per-model skills, price,
        |  calibrated P(success), cost  |      context, latency
        +---------------+---------------+
                        |  mode: max_utility (default) | max_quality | cheapest_above_threshold
                        v
        choice + ranking + escalation_ladder + trace_id
              -> you run it and verify -> /outcome   (on failure: /escalate -> next model)
```

Features: pool name aliases (your exact string is echoed back, `card_id` shows the match), newer versions
supersede older ones when they are not pricier, an escalation ladder that `/escalate` follows after a failure, SQLite
outcome logging, an HTTP server, a CLI, a Python API and an MCP server.

> The router returns a model *name*. It does not call the model or check its answer. See
> [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md) for how to turn the pick into `claude --model`, `codex -m`,
> `ollama run` or an OpenRouter slug, and [docs/BEST_RESULTS.md](docs/BEST_RESULTS.md) for the route, verify,
> escalate loop that gets the best results.

## Quickstart

Requires Python 3.12+.

```sh
git clone https://github.com/AICodeKing/PandaOrchestrator.git
cd PandaOrchestrator
python3.12 -m venv .venv && . .venv/bin/activate
pip install -e .            # core: serving only (onnxruntime, transformers tokenizer, numpy, scipy, jsonschema; no torch)
pip install -e ".[train]"   # optional: torch and friends, only needed to retrain or export (see docs below)
```

The trained profiler and success head ship in the repo at `artifacts/panda-router-v4/` (31 MB int8 ONNX
`model.int8.onnx`, `heads.json`, `success_head.json`, tokenizer files). The CLI, the HTTP server and the MCP server
all default to that directory in a source checkout (or `$PANDA_ROUTER_ARTIFACTS`); outside one they fall back to a
keyword heuristic profiler, which works but is clearly weaker. An explicitly given `--artifacts` directory that fails
to load is an error, not a silent fallback.

**Route one task (CLI)**

```sh
panda-router route --artifacts artifacts/panda-router-v4 --no-log \
  --task 'Rename a variable in utils.py' \
  --pool claude/sonnet-5-5,claude-haiku-5.5,gpt-oss:20b --mode max_utility --top-k 3
```

`panda-router route` prints a RouteResponse as JSON. Add `--profile` to include the full TaskProfile,
`--context '{"repo_languages":["python"],"files_in_scope":2}'` for hints, `--local-only`, `--max-cost USD`,
`--min-p 0.5`. All flags are listed in [docs/API.md](docs/API.md#cli). The CLI loads the model on every call; for
loops use the server.

**Start the HTTP server**

```sh
panda-router-serve --port 8765 --artifacts artifacts/panda-router-v4
# [panda-router] listening on http://127.0.0.1:8765 (profiler=OnnxProfiler(panda-router-v4/model.int8.onnx), ...)
curl -s localhost:8765/health
```

**Start the MCP server (stdio)**

```sh
panda-router-mcp --artifacts artifacts/panda-router-v4
```

It speaks newline-delimited JSON-RPC on stdin/stdout and exposes `route_task`, `escalate_task`,
`record_outcome` and `list_models`. Clients normally launch it for you; see
[docs/INTEGRATIONS.md](docs/INTEGRATIONS.md). In a source checkout, `--artifacts` defaults to
`artifacts/panda-router-v4` when that directory exists.

## Example

```sh
curl -s -X POST localhost:8765/route -H 'content-type: application/json' -d '{
  "task": {"text": "Migrate our Express auth middleware to use JWT refresh tokens and update all call sites",
           "context": {"repo_languages": ["typescript"], "files_in_scope": 12}},
  "pool": ["claude-sonnet-5.5", "claude-haiku-5.5", "codex-gpt-6-luna", "ollama-qwen3-coder-30b"],
  "preferences": {"mode": "cheapest_above_threshold", "min_p_success": 0.5},
  "return_top_k": 2
}'
```

Real output, trimmed to the main fields (full field list in [docs/API.md](docs/API.md#post-route)):

```json
{
  "choice": {"model_id": "claude-sonnet-5.5", "confidence": 0.6227, "confidence_lower": 0.5427,
             "decided_by": "policy:cheapest_above_threshold", "propensity": 1.0, "explored": false},
  "ranking": [
    {"model_id": "claude-sonnet-5.5", "card_id": "claude-sonnet-5.5", "p_success": 0.6227, "p_success_lower": 0.5427,
     "p_source": "success_head", "est_cost_usd": 0.018252, "expected_cost_usd": 0.027815, "est_latency_ms": 21146.7},
    {"model_id": "claude-haiku-5.5", "card_id": "claude-haiku-5.5", "p_success": 0.5042, "p_success_lower": 0.4565,
     "p_source": "success_head", "est_cost_usd": 0.000913, "expected_cost_usd": 0.021702, "est_latency_ms": 11923.1}
  ],
  "difficulty": {"level": 5, "expected": 4.89, "decision_level": 5.382, "vagueness": 0.0},
  "category": {"label": "implementation", "p": 0.7906},
  "escalation_ladder": [
    {"model_id": "claude-haiku-5.5", "p_success": 0.5042, "p_success_lower": 0.4565, "est_cost_usd": 0.000913},
    {"model_id": "claude-sonnet-5.5", "p_success": 0.6227, "p_success_lower": 0.5427, "est_cost_usd": 0.018252},
    {"model_id": "codex-gpt-6-luna", "p_success": 0.3093, "p_success_lower": 0.2727, "est_cost_usd": 0.000913}
  ],
  "escalation_ladder_note": "try in order, escalate on failure; independent-failure estimate of success within 2 attempts >= 0.75",
  "router": {"policy": "v4", "success_head": "success_head_v4(panda-router-v4)", "latency_ms": 10.228},
  "trace_id": "r_dc1daf912043483d80cdd510"
}
```

`p_success` is a calibrated, strict-grading pass rate, and decisions use `p_success_lower`. The cheapest model whose
lower bound clears `min_p_success` (0.5) is `claude-sonnet-5.5`; haiku is cheaper but its bound is 0.46. If you verify
the result and it fails, `POST /escalate` returns the next model on the ladder. Report each attempt with
`POST /outcome`. Details: [docs/API.md](docs/API.md).

### Getting the best results

A single pick scores 74-82 per 100 tasks; a verified retry scores 89-92. Full guide:
**[docs/BEST_RESULTS.md](docs/BEST_RESULTS.md)**.

- **Close the loop.** Route, run `escalation_ladder[0]`, verify (tests, lint, a reviewer or a cheap LLM check), on a
  failure `POST /escalate`, and stop after 2 retries.
- **Pick the mode for your risk.** `max_utility` (default); `max_quality` when a failure is expensive and you cannot
  verify; `cheapest_above_threshold` for bulk easy work.
- **Keep `min_p_success` near 0.5.** Calibrated P rarely exceeds about 0.65, so 0.75 usually falls back to the
  safest model (`decided_by` ends `:relaxed`).
- **Pass only models you can run.** The default pool is all 65 cards, including OpenRouter and Ollama ones you may
  not have.
- **Give context and write real tasks.** `repo_languages`, `files_in_scope`, `estimated_input_tokens`, `has_images`,
  `requires_tools`; scope and acceptance criteria. Vague requests are rated harder on purpose.
- **Always send `/outcome`**, failures too, with cost and latency; it is the data any later refit needs.
- **Cap spend** with `max_cost_usd`, `local_only` and `exclude`, and read `est_cost_usd`.

## Results

### Real routed success (v4.2)

150 held-out real tasks, each actually attempted by nine models (claude-haiku/sonnet/opus-5.5, codex-gpt-6-luna,
gpt-6.1-sol, gemini-3.8-flash, deepseek-v4.1-flash, minimax-m3.1-flash, qwen3.8-flash) and graded pass/fail by an
LLM judge (DeepSeek, then GPT-5.6-Terra; agreement with a Kimi K3.1 Pro reference kappa 0.70-0.85). Nothing was
tuned on these tasks. Reports: [eval_reports/v4/REPORT.md](eval_reports/v4/REPORT.md),
[data/outcomes/REPORT_v4_attempts.md](data/outcomes/REPORT_v4_attempts.md).

| strategy | success / 100 | $ / 100 tasks |
|---|---:|---:|
| v4.2, single pick, `max_utility` (default) | 77.3 | 0.99 |
| v4.2, single pick, `max_quality` | 82.0 | 1.20 |
| v4.2, single pick, `cheapest_above_threshold` | 74.0 | 0.74 |
| **v4, follow `escalation_ladder`, up to 2 attempts** | **88.7 [83.3, 93.3]** | **0.88** |
| v4, escalate from `choice` (`max_utility`), up to 2 attempts | 90.7 | 1.68 |
| v4.2, up to 3 attempts | 92.0 | 1.23 |
| always best single model (gpt-6.1-sol) | 79.3 [72.7, 85.3] | 1.11 |
| always strongest-priced (claude-opus-5.5) | 76.7 | 4.03 |
| oracle (cheapest model that passed) | 94.0 | 0.56 |

Costs are estimates from card prices and logged token counts. Single-pick 95% intervals are about +-7 points, so
`max_utility` vs always-sol is within noise; `max_quality` (82.0 [75.3, 88.0]) is the best single pick.

- **85+ needs one retry.** Following the response's `escalation_ladder` (cheap-but-safe first, stronger next) when
  your orchestrator can tell a failure (tests, review, a verifier) gets 88.7/100 for less than always-sol. In this
  simulation the judge's label was the failure signal. How to build the loop: [docs/BEST_RESULTS.md](docs/BEST_RESULTS.md).
- **The three modes differ.** `max_quality` is the safest single pick, `cheapest_above_threshold` trades about 3
  points for 25% lower cost, `max_utility` sits between.
- **$0 models no longer win by default.** Expected cost includes the cost of failing and retrying; free and
  weak-evidence cards get a conservative prior. $0 picks on the full pool in cheapest mode: 88% (v3) -> 0%.
- **Errs on the safe side.** Decisions use `p_success_lower` (a lower confidence bound); the profiler is trained
  to over- rather than under-estimate difficulty. Under-powered picks fell from 27% (v3) to 14% (`max_quality`: 9%).
- **`p_success` is an honest, strict-grading pass rate** (calibrated per model on train/val, ECE 0.015). It looks
  low for trivial questions (~0.5) because the outcome data has few trivial, well-specified tasks ([known limitation](eval_reports/v4/REPORT.md#known-limitation-p-for-trivial-tasks-is-understated)).
- **Vague requests** ("a model trainer") are rated ~5 instead of 1.5 and go to a paid model.

### Profiler quality (v1-v3 history; v4 = v3 data + Modal-trained 150M teacher, distilled 32M, vague-task fine-tune)

Evaluated on 359 real tasks (the gold set) that were never trained on, labelled by Codex + DeepSeek V4.1 Flash.
Full tables: [eval_reports/compare_v3.md](eval_reports/compare_v3.md); release notes: [RESULTS.md](RESULTS.md) (v4 first).

| profiler | gold category acc | gold difficulty MAE / rho | gold flags AUROC | attempt-IRT rho | SWE held-out rho | hard-task pass |
|---|---:|---:|---:|---:|---:|---:|
| v1 | 0.624 | 0.900 / 0.675 | 0.885 | 0.178 | 0.025 | 0.80 |
| v2 | 0.641 | 0.897 / 0.705 | 0.886 | 0.115 | **0.119** | 0.85 |
| **v3** | **0.688** | **0.825 / 0.747** | **0.901** | **0.212** | 0.081 | 0.85 |

- v4 keeps the 32M architecture and trades some difficulty rank correlation for a deliberate over-estimate: on gold,
  the v4 candidates' difficulty bias moved from -0.14 (v3) to +0.05..+0.12 and gold rho to 0.71-0.73 (v3: 0.747);
  hard-task pass 0.85 -> 0.90-0.95 ([eval_reports/v4_profiler/REPORT.md](eval_reports/v4_profiler/REPORT.md); the
  shipped weights are a WiSE 0.7/0.3 blend of the fine-tune and the soup and were not re-tabulated there).
- v3 was a direct Ettin-32M trained on 8,247 tasks (every row labelled by at least two teachers, DeepSeek V4.1
  Flash on all of them) with real-outcome difficulty from SWE-bench and from the attempt-and-grade runs as an
  auxiliary target (weight 0.3). 31 MB int8.
- *attempt-IRT rho*: rank correlation between predicted difficulty and difficulty fitted from the real
  attempts above. *SWE held-out rho*: the same against SWE-bench item difficulty on repos never trained on; v3 is
  lower here than v2 (0.08 vs 0.12, both weak).
- Latency: v1-v4 share one 32M architecture; on an idle host the profiler runs at about 10 ms p50 / 19 ms p95
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
panda_router/     serve/ (Router, HTTP server, CLI), mcp/ (stdio MCP server), matcher/, router_v4/ (success head,
                  policy, ladder), model/ (net, ONNX profiler), train/, datagen/, outcomes/, eval/, heuristic.py
cards/            one JSON per model (+ optional/ for free tiers)
schemas/          JSON Schemas for requests, responses, outcomes, cards; CONTRACTS.md; taxonomy.json
scripts/          datagen/, train/, eval/, outcomes/ (success head, card fits), modal/ (GPU training) entry points
data/             training data, gold set, outcome fits (STATS.md, gold/README.md, outcomes/REPORT.md)
eval_reports/     comparison tables and per-model reports
docs/             API.md, BEST_RESULTS.md, INTEGRATIONS.md, CARDS.md
tests/            pytest suite
RESULTS.md        v4 release notes (then v3, v2)
PLAN.md           design plan
```

## Training and reproduction

Install the `[train]` extra, then follow [panda_router/train/README.md](panda_router/train/README.md) (teacher,
distillation, soup, calibration, ONNX export, latency bench, outcome anchors, the v4 Modal jobs and the success head).
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

Teacher labels were produced by LLMs (Codex, DeepSeek V4.1 Flash and others; see [data/STATS.md](data/STATS.md)), so they carry those models' biases. Repo code inside SWE-rebench keeps its own licence.
More detail per source: [data/gold/README.md](data/gold/README.md) and [data/outcomes/REPORT.md](data/outcomes/REPORT.md).
