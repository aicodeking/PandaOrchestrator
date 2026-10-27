# v4 attempt-and-grade: dsh judge and subscription attempters (2026-10-27)

No OpenRouter calls were made. Judges: stored ds-think labels where they exist, `dsh --profile headless` (DeepSeek) for
930 cells before its balance ran out, and `gpt-5.6-terra` via `codex exec` for the other 3,191. Claude models ran through
`claude -p` (no tools, own system prompt, `--effort low`), and gpt-6-luna through `codex exec` (read-only, bare
CODEX_HOME, reasoning effort low). The attempt system prompt is the one used for the OpenRouter attempters.
Thinking budgets are **not** capped for the Claude models (neither flag nor env var limited it in a test), unlike the
1,500-token cap on the OpenRouter models. Code: `panda_router/outcomes/cli_chat.py`, `scripts/outcomes/attempts_v4.py`,
`build_attempts.py` (9 models), `report_v4.py`.

## Judge parity

Same fixed 100-answer gold validation sample (cells with both stored ds-think and kimi-k3.1-pro grades) for all pairs;
n differs slightly where a judge returned no parseable verdict. The dsh harness judge (`dsh --profile headless`, same
JUDGE_PROMPT and rubric) reached kappa 0.745 vs ds-think, just under the 0.75 bar, but 0.77 vs the neutral kimi judge.
It then ran out of balance ("QUOTA: Insufficient Balance") after 1,029 train/val+gold cells; the 3,133 failed dsh calls are
error rows and are not counted. The remaining cells were graded by `gpt-5.6-terra` through `codex exec` (not an attempter,
so no self-grading), 10 items per prompt with the same rubric, bar kappa >= 0.7 vs kimi (`scripts/outcomes/judge_terra.py`).

| pair | n gold cells | agreement | Cohen kappa (95% CI) | pass rate (first / second) |
|---|---|---|---|---|
| dsh vs ds-think | 99 | 0.879 | 0.746 (0.60-0.87) | 0.60 / 0.62 |
| dsh vs kimi | 99 | 0.889 | 0.768 (0.63-0.89) | 0.60 / 0.61 |
| codex-terra vs ds-think | 99 | 0.848 | 0.681 (0.53-0.82) | 0.61 / 0.62 |
| codex-terra vs kimi | 99 | 0.859 | 0.704 (0.57-0.83) | 0.61 / 0.61 |
| ds-think vs kimi | 99 | 0.929 | 0.851 (0.74-0.96) | 0.62 / 0.61 |

Judge mix of the labels used (train/val | gold): codex-terra train/val: 3191, ds-think gold: 734, ds-think train/val: 2204, dsh gold: 616, dsh train/val: 314

Label rule: ds-think > dsh > codex-terra. Only cells with a valid grade enter the fit.

## Coverage and gold pass rates

| model | train/val tasks graded | gold tasks graded | gold pass % | train/val pass % | gold answers cut at length |
|---|---|---|---|---|---|
| openrouter-deepseek-v4.1-flash | 877 | 150 | 65.3 | 35.1 | 11% |
| openrouter-qwen3.8-flash | 869 | 150 | 45.3 | 18.8 | 5% |
| openrouter-minimax-m3.1-flash | 875 | 150 | 45.3 | 22.9 | 5% |
| openrouter-gemini-3.8-flash | 874 | 150 | 60.7 | 30.3 | 1% |
| openrouter-gpt-6.1-sol | 864 | 150 | 79.3 | 57.6 | 0% |
| claude-haiku-5.5 | 400 | 150 | 64.0 | 44.0 | 0% |
| claude-sonnet-5.5 | 400 | 150 | 73.3 | 52.8 | 0% |
| claude-opus-5.5 | 150 | 150 | 76.7 | 48.0 | 0% |
| codex-gpt-6-luna | 400 | 150 | 51.3 | 29.0 | 0% |

## Baselines on the gold pool

$ is estimated from card prices x tokens: logged prompt/completion tokens for the OpenRouter models, and
(system + task chars)/4 input plus logged output tokens (thinking included) for the subscription models (no cache
discount, so Claude/luna costs are upper-ish bounds).

**9-model pool: 150 gold tasks with every model graded.**

| strategy | success / 100 | est. $ / 100 |
|---|---|---|
| always openrouter-deepseek-v4.1-flash | 65.3 | 0.245 |
| always openrouter-qwen3.8-flash | 45.3 | 0.067 |
| always openrouter-minimax-m3.1-flash | 45.3 | 0.122 |
| always openrouter-gemini-3.8-flash | 60.7 | 0.542 |
| always openrouter-gpt-6.1-sol | 79.3 | 1.109 |
| always claude-haiku-5.5 | 64.0 | 0.121 |
| always claude-sonnet-5.5 | 73.3 | 2.040 |
| always claude-opus-5.5 | 76.7 | 4.030 |
| always codex-gpt-6-luna | 51.3 | 0.035 |
| ORACLE (cheapest passing model) | 94.0 | 0.223 |

**4 subscription models only: 150 gold tasks with every model graded.**

| strategy | success / 100 | est. $ / 100 |
|---|---|---|
| always claude-haiku-5.5 | 64.0 | 0.121 |
| always claude-sonnet-5.5 | 73.3 | 2.040 |
| always claude-opus-5.5 | 76.7 | 4.030 |
| always codex-gpt-6-luna | 51.3 | 0.035 |
| ORACLE (cheapest passing model) | 91.3 | 0.591 |

## Card updates (applied, provenance 'verified (attempt-grade v4)')

IRT: 1PL, 7059 graded cells, joint over 9 models, link anchored on the 9 cards' own mean thetas (so deltas are
relative to the cards' consensus, not absolute). An axis is updated only with >= 25 items on that axis and a delta above the
combined uncertainty; for the 5 OpenRouter models the direction must also hold under gpt-6.1-sol grading (not available for
the 4 subscription models). `supersedes` is untouched.

| card | card mean | fitted mean | delta | axes updated |
|---|---|---|---|---|
| openrouter-deepseek-v4.1-flash | 7.49 | 7.69 (+-0.28) | +0.20 | none |
| openrouter-qwen3.8-flash | 6.59 | 6.59 (+-0.28) | -0.00 | none |
| openrouter-minimax-m3.1-flash | 7.24 | 6.89 (+-0.28) | -0.34 | data_analysis 7.5->6.76 (n=63), research 7.4->6.47 (n=34), ui_frontend 7.6->6.6 (n=46), writing 7.5->6.8 (n=118) |
| openrouter-gemini-3.8-flash | 7.53 | 7.4 (+-0.28) | -0.13 | review 7.8->7.11 (n=49) |
| openrouter-gpt-6.1-sol | 8.52 | 8.97 (+-0.28) | +0.45 | coding 8.6->9.25 (n=133), data_analysis 8.3->9.1 (n=63) |
| claude-haiku-5.5 | 6.72 | 8.16 (+-0.29) | +1.44 | coding 7.0->8.35 (n=64), debugging 6.8->8.71 (n=52), planning 6.5->7.9 (n=40), reasoning 6.7->8.16 (n=52), review 6.8->8.29 (n=27), writing 7.2->7.77 (n=63) |
| claude-sonnet-5.5 | 8.28 | 8.65 (+-0.29) | +0.37 | debugging 8.4->9.15 (n=52) |
| claude-opus-5.5 | 8.94 | 8.38 (+-0.32) | -0.56 | coding 9.3->8.62 (n=31) |
| codex-gpt-6-luna | 7.27 | 7.27 (+-0.29) | +0.00 | coding 7.7->6.76 (n=64), planning 7.1->7.78 (n=40) |

Caveats: the three judges differ (kappa 0.68-0.75 pairwise vs ds-think), so cross-judge pass rates carry a few points of
noise; train/val cells of the 4 new models cover 400 tasks (opus 150), so their axis evidence is thinner; Claude models
ran with uncapped thinking, which favours them against the 1,500-token-capped OpenRouter models. Haiku-5.5 moved up by
~1.4 theta (card was seeded low); opus moved down (-0.7 coding, only 31 items). The oracle (94.0 on 9 models, 91.3 on
the 4 subscription models) is an upper bound on routing and uses the judge labels as truth.

Files: `data/outcomes/{attempts,tasks_attempts,gold_attempts,success_cells}.jsonl`, `fit_attempts.json`,
`card_deltas_attempts.json`. `success_cells.jsonl`: task_id, split (train/val/gold; gold = evaluation only), text,
card_id, pass, judge.
