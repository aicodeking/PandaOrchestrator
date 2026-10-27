# Gold attempt-and-grade outcome evaluation

IRT difficulty Spearman on held-out gold attempts (n=150): **0.2117** (predicted mean/sd 3.713/1.211).

True routed outcomes use the 140 gold tasks graded for every attempter; cost is logged attempt cost only.

| policy | success / 100 | $ / 100 tasks | picks |
|---|---:|---:|---|
| always_cheapest | 47.1 | 0.064 | openrouter-qwen3.8-flash: 140 |
| always_strongest | 78.6 | 1.061 | openrouter-gpt-6.1-sol: 140 |
| cheapest_above_threshold | 51.4 | 0.142 | openrouter-deepseek-v4.1-flash: 2, openrouter-gpt-6.1-sol: 5, openrouter-minimax-m3.1-flash: 9, openrouter-qwen3.8-flash: 124 |
| max_utility | 67.9 | 0.156 | openrouter-deepseek-v4.1-flash: 139, openrouter-gpt-6.1-sol: 1 |
| max_quality | 78.6 | 1.061 | openrouter-gpt-6.1-sol: 140 |
