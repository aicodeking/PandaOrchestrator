# Gold attempt-and-grade outcome evaluation

IRT difficulty Spearman on held-out gold attempts (n=150): **0.1777** (predicted mean/sd 3.612/1.083).

True routed outcomes use the 140 gold tasks graded for every attempter; cost is logged attempt cost only.

| policy | success / 100 | $ / 100 tasks | picks |
|---|---:|---:|---|
| always_cheapest | 47.1 | 0.064 | openrouter-qwen3.8-flash: 140 |
| always_strongest | 78.6 | 1.061 | openrouter-gpt-6.1-sol: 140 |
| cheapest_above_threshold | 47.9 | 0.111 | openrouter-gemini-3.8-flash: 2, openrouter-gpt-6.1-sol: 3, openrouter-minimax-m3.1-flash: 9, openrouter-qwen3.8-flash: 126 |
| max_utility | 45.7 | 0.114 | openrouter-minimax-m3.1-flash: 140 |
| max_quality | 78.6 | 1.061 | openrouter-gpt-6.1-sol: 140 |
