# Gold attempt-and-grade outcome evaluation

IRT difficulty Spearman on held-out gold attempts (n=150): **0.1371** (predicted mean/sd 4.006/1.174).

True routed outcomes use the 150 gold tasks graded for every attempter; cost is logged attempt cost only.

| policy | success / 100 | $ / 100 tasks | picks |
|---|---:|---:|---|
| always_cheapest | 45.3 | 0.067 | openrouter-qwen3.8-flash: 150 |
| always_strongest | 79.3 | 1.114 | openrouter-gpt-6.1-sol: 150 |
| cheapest_above_threshold | 50.7 | 0.169 | openrouter-deepseek-v4.1-flash: 11, openrouter-gpt-6.1-sol: 8, openrouter-minimax-m3.1-flash: 15, openrouter-qwen3.8-flash: 116 |
| max_utility | 65.3 | 0.166 | openrouter-deepseek-v4.1-flash: 148, openrouter-gpt-6.1-sol: 2 |
| max_quality | 79.3 | 1.114 | openrouter-gpt-6.1-sol: 150 |
