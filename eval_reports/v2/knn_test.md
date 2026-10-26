# Eval: `knn` on `test` (n=364)

Sources: {'minimal-pair': 78, 'swe-rebench': 53, 'swe-smith': 20, 'synthetic': 148, 'wildchat': 65}  
Latency (batch 1): p50 60.302 ms, p95 254.418 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.555 / 0.679 / 0.093 |
| difficulty | MAE / Spearman / QWK / ECE | 1.067 / 0.775 / 0.703 / 0.032 |
| skills | mean MAE / mean Spearman / mean ECE | 1.151 / 0.682 / 0.115 |
| flags | F1 macro / AUROC macro / ECE | 0.554 / 0.833 / 0.076 |
| checklist | F1 macro / micro / AUROC | 0.601 / 0.735 / 0.839 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.264 / 0.882 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 78 | 0.513 | 1.053 | 0.760 | 0.593 | 0.574 |
| swe-rebench | 53 | 0.717 | 0.890 | 0.282 | 0.528 | 0.348 |
| swe-smith | 20 | 1.000 | 0.824 | 0.211 | 0.375 | 0.463 |
| synthetic | 148 | 0.453 | 1.107 | 0.687 | 0.567 | 0.616 |
| wildchat | 65 | 0.569 | 1.208 | 0.490 | 0.212 | 0.267 |

## Routing (cards: cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 18170 | 0.605 | -0.0214 | 1.092 | 0.794 | 0.293 | 0.603 | 0.550 | 0.000 |
| predicted | max_utility | 18170 | 0.841 | 0.0017 | 0.891 | 0.798 | 0.288 | 0.632 | 0.632 | 0.000 |
| predicted | max_quality | 18170 | 0.988 | 0.0004 | 1.005 | 0.830 | 0.236 | 0.696 | 0.696 | 0.000 |
| predicted | all | 54510 | 0.811 | -0.0064 | 1.000 | 0.807 | 0.272 | 0.644 | 0.626 | 0.000 |
| always_strongest | cheapest_above_threshold | 18170 | 0.388 | 0.0187 | 1.628 | 0.821 | 0.243 | 0.690 | 0.550 | 0.014 |
| always_strongest | max_utility | 18170 | 0.401 | 0.0939 | 1.743 | 0.821 | 0.243 | 0.690 | 0.632 | 0.014 |
| always_strongest | max_quality | 18170 | 0.964 | 0.0157 | 1.006 | 0.821 | 0.243 | 0.690 | 0.696 | 0.014 |
| always_strongest | all | 54510 | 0.584 | 0.0428 | 1.375 | 0.821 | 0.243 | 0.690 | 0.626 | 0.014 |
| always_cheapest | cheapest_above_threshold | 18170 | 0.165 | 0.3111 | 0.015 | 0.400 | 0.760 | 0.218 | 0.550 | 0.082 |
| always_cheapest | max_utility | 18170 | 0.059 | 0.3863 | 0.016 | 0.400 | 0.760 | 0.218 | 0.632 | 0.082 |
| always_cheapest | max_quality | 18170 | 0.014 | 0.3081 | 0.009 | 0.400 | 0.760 | 0.218 | 0.696 | 0.082 |
| always_cheapest | all | 54510 | 0.079 | 0.3352 | 0.012 | 0.400 | 0.760 | 0.218 | 0.626 | 0.082 |
