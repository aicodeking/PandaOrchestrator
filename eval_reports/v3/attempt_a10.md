# Gold attempt-and-grade outcome evaluation

IRT difficulty Spearman on held-out gold attempts (n=150): **0.1639** (predicted mean/sd 4.322/1.156).

True routed outcomes use the 140 gold tasks graded for every attempter; cost is logged attempt cost only.

| policy | success / 100 | $ / 100 tasks | picks |
|---|---:|---:|---|
| always_cheapest | 47.1 | 0.064 | openrouter-qwen3.8-flash: 140 |
| always_strongest | 78.6 | 1.061 | openrouter-gpt-6.1-sol: 140 |
| cheapest_above_threshold | 78.6 | 1.061 | openrouter-gpt-6.1-sol: 140 |
| max_utility | 72.1 | 0.963 | openrouter-gemini-3.8-flash: 7, openrouter-gpt-6.1-sol: 109, openrouter-minimax-m3.1-flash: 24 |
| max_quality | 78.6 | 1.061 | openrouter-gpt-6.1-sol: 140 |
