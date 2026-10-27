# Gold attempt-and-grade outcome evaluation

IRT difficulty Spearman on held-out gold attempts (n=150): **0.1153** (predicted mean/sd 3.545/1.102).

True routed outcomes use the 140 gold tasks graded for every attempter; cost is logged attempt cost only.

| policy | success / 100 | $ / 100 tasks | picks |
|---|---:|---:|---|
| always_cheapest | 47.1 | 0.064 | openrouter-qwen3.8-flash: 140 |
| always_strongest | 78.6 | 1.061 | openrouter-gpt-6.1-sol: 140 |
| cheapest_above_threshold | 50.0 | 0.095 | openrouter-gpt-6.1-sol: 2, openrouter-minimax-m3.1-flash: 10, openrouter-qwen3.8-flash: 128 |
| max_utility | 45.7 | 0.114 | openrouter-minimax-m3.1-flash: 140 |
| max_quality | 78.6 | 1.061 | openrouter-gpt-6.1-sol: 140 |
