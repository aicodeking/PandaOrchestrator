# Gold attempt-and-grade outcome evaluation

IRT difficulty Spearman on held-out gold attempts (n=150): **0.2620** (predicted mean/sd 3.917/1.221).

True routed outcomes use the 150 gold tasks graded for every attempter; cost is logged attempt cost only.

| policy | success / 100 | $ / 100 tasks | picks |
|---|---:|---:|---|
| always_cheapest | 45.3 | 0.067 | openrouter-qwen3.8-flash: 150 |
| always_strongest | 79.3 | 1.114 | openrouter-gpt-6.1-sol: 150 |
| cheapest_above_threshold | 51.3 | 0.216 | openrouter-deepseek-v4.1-flash: 13, openrouter-gpt-6.1-sol: 11, openrouter-minimax-m3.1-flash: 4, openrouter-qwen3.8-flash: 122 |
| max_utility | 65.3 | 0.152 | openrouter-deepseek-v4.1-flash: 150 |
| max_quality | 79.3 | 1.114 | openrouter-gpt-6.1-sol: 150 |
