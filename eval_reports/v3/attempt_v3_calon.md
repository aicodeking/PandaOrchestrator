# Gold attempt-and-grade outcome evaluation

IRT difficulty Spearman on held-out gold attempts (n=150): **0.2117** (predicted mean/sd 3.713/1.211).

True routed outcomes use the 140 gold tasks graded for every attempter; cost is logged attempt cost only.

| policy | success / 100 | $ / 100 tasks | picks |
|---|---:|---:|---|
| always_cheapest | 47.1 | 0.064 | openrouter-qwen3.8-flash: 140 |
| always_strongest | 78.6 | 1.061 | openrouter-gpt-6.1-sol: 140 |
| cheapest_above_threshold | 78.6 | 1.061 | openrouter-gpt-6.1-sol: 140 |
| max_utility | 76.4 | 0.832 | openrouter-deepseek-v4.1-flash: 62, openrouter-gemini-3.8-flash: 1, openrouter-gpt-6.1-sol: 77 |
| max_quality | 78.6 | 1.061 | openrouter-gpt-6.1-sol: 140 |
