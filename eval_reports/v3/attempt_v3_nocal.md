# Gold attempt-and-grade outcome evaluation

IRT difficulty Spearman on held-out gold attempts (n=150): **0.2117** (predicted mean/sd 3.713/1.211).

True routed outcomes use the 140 gold tasks graded for every attempter; cost is logged attempt cost only.

| policy | success / 100 | $ / 100 tasks | picks |
|---|---:|---:|---|
| always_cheapest | 47.1 | 0.064 | openrouter-qwen3.8-flash: 140 |
| always_strongest | 78.6 | 1.061 | openrouter-gpt-6.1-sol: 140 |
| cheapest_above_threshold | 50.7 | 0.149 | openrouter-gemini-3.8-flash: 2, openrouter-gpt-6.1-sol: 5, openrouter-minimax-m3.1-flash: 9, openrouter-qwen3.8-flash: 124 |
| max_utility | 45.0 | 0.152 | openrouter-gemini-3.8-flash: 6, openrouter-gpt-6.1-sol: 2, openrouter-minimax-m3.1-flash: 132 |
| max_quality | 78.6 | 1.061 | openrouter-gpt-6.1-sol: 140 |
