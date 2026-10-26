# Eval: `onnx:artifacts/abl32m_direct` on `test` (n=300)

Sources: {'minimal-pair': 89, 'swe-rebench': 53, 'swe-smith': 7, 'synthetic': 68, 'wildchat': 83}  
Latency (batch 1): p50 16.842 ms, p95 63.007 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.667 / 0.803 / 0.061 |
| difficulty | MAE / Spearman / QWK / ECE | 0.836 / 0.818 / 0.792 / 0.012 |
| skills | mean MAE / mean Spearman / mean ECE | 0.935 / 0.728 / 0.112 |
| flags | F1 macro / AUROC macro / ECE | 0.781 / 0.902 / 0.052 |
| checklist | F1 macro / micro / AUROC | 0.697 / 0.768 / 0.888 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.218 / 0.733 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 89 | 0.652 | 0.845 | 0.861 | 0.773 | 0.715 |
| swe-rebench | 53 | 0.830 | 0.771 | 0.448 | 0.706 | 0.387 |
| swe-smith | 7 | 1.000 | 0.682 | 0.741 | 0.417 | 0.600 |
| synthetic | 68 | 0.662 | 0.602 | 0.702 | 0.845 | 0.744 |
| wildchat | 83 | 0.554 | 1.073 | 0.597 | 0.248 | 0.368 |

## Routing (cards: cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 14978 | 0.714 | 0.0092 | 0.972 | 0.819 | 0.249 | 0.608 | 0.623 | 0.001 |
| predicted | max_utility | 14978 | 0.853 | 0.0027 | 0.913 | 0.862 | 0.192 | 0.700 | 0.710 | 0.000 |
| predicted | max_quality | 14978 | 0.989 | 0.0012 | 1.012 | 0.903 | 0.118 | 0.793 | 0.793 | 0.000 |
| predicted | all | 44934 | 0.852 | 0.0044 | 0.976 | 0.862 | 0.186 | 0.701 | 0.709 | 0.000 |
| always_strongest | cheapest_above_threshold | 14978 | 0.260 | 0.0357 | 1.805 | 0.902 | 0.120 | 0.792 | 0.623 | 0.003 |
| always_strongest | max_utility | 14978 | 0.249 | 0.1019 | 1.903 | 0.902 | 0.120 | 0.792 | 0.710 | 0.003 |
| always_strongest | max_quality | 14978 | 0.985 | 0.0044 | 1.013 | 0.902 | 0.120 | 0.792 | 0.793 | 0.003 |
| always_strongest | all | 44934 | 0.498 | 0.0474 | 1.452 | 0.902 | 0.120 | 0.792 | 0.709 | 0.003 |
| always_cheapest | cheapest_above_threshold | 14978 | 0.345 | 0.2248 | 0.055 | 0.555 | 0.608 | 0.348 | 0.623 | 0.046 |
| always_cheapest | max_utility | 14978 | 0.137 | 0.2910 | 0.058 | 0.555 | 0.608 | 0.348 | 0.710 | 0.046 |
| always_cheapest | max_quality | 14978 | 0.013 | 0.1936 | 0.031 | 0.555 | 0.608 | 0.348 | 0.793 | 0.046 |
| always_cheapest | all | 44934 | 0.165 | 0.2365 | 0.045 | 0.555 | 0.608 | 0.348 | 0.709 | 0.046 |
