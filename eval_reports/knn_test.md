# Eval: `knn` on `test` (n=300)

Sources: {'minimal-pair': 89, 'swe-rebench': 53, 'swe-smith': 7, 'synthetic': 68, 'wildchat': 83}  
Latency (batch 1): p50 30.387 ms, p95 55.888 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.470 / 0.670 / 0.086 |
| difficulty | MAE / Spearman / QWK / ECE | 1.107 / 0.691 / 0.612 / 0.075 |
| skills | mean MAE / mean Spearman / mean ECE | 1.193 / 0.595 / 0.123 |
| flags | F1 macro / AUROC macro / ECE | 0.504 / 0.758 / 0.086 |
| checklist | F1 macro / micro / AUROC | 0.542 / 0.685 / 0.789 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.289 / 0.830 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 89 | 0.472 | 1.170 | 0.775 | 0.463 | 0.530 |
| swe-rebench | 53 | 0.736 | 0.853 | 0.376 | 0.448 | 0.316 |
| swe-smith | 7 | 1.000 | 1.004 | 0.556 | 0.250 | 0.607 |
| synthetic | 68 | 0.338 | 0.736 | 0.584 | 0.637 | 0.617 |
| wildchat | 83 | 0.361 | 1.514 | 0.303 | 0.304 | 0.306 |

## Routing (cards: cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 14978 | 0.602 | -0.0054 | 0.942 | 0.835 | 0.232 | 0.641 | 0.623 | 0.000 |
| predicted | max_utility | 14978 | 0.809 | 0.0042 | 0.859 | 0.863 | 0.189 | 0.707 | 0.710 | 0.000 |
| predicted | max_quality | 14978 | 0.989 | 0.0012 | 1.012 | 0.903 | 0.118 | 0.793 | 0.793 | 0.000 |
| predicted | all | 44934 | 0.800 | -0.0000 | 0.954 | 0.867 | 0.180 | 0.714 | 0.709 | 0.000 |
| always_strongest | cheapest_above_threshold | 14978 | 0.260 | 0.0357 | 1.805 | 0.902 | 0.120 | 0.792 | 0.623 | 0.003 |
| always_strongest | max_utility | 14978 | 0.249 | 0.1019 | 1.903 | 0.902 | 0.120 | 0.792 | 0.710 | 0.003 |
| always_strongest | max_quality | 14978 | 0.985 | 0.0044 | 1.013 | 0.902 | 0.120 | 0.792 | 0.793 | 0.003 |
| always_strongest | all | 44934 | 0.498 | 0.0474 | 1.452 | 0.902 | 0.120 | 0.792 | 0.709 | 0.003 |
| always_cheapest | cheapest_above_threshold | 14978 | 0.345 | 0.2248 | 0.055 | 0.555 | 0.608 | 0.348 | 0.623 | 0.046 |
| always_cheapest | max_utility | 14978 | 0.137 | 0.2910 | 0.058 | 0.555 | 0.608 | 0.348 | 0.710 | 0.046 |
| always_cheapest | max_quality | 14978 | 0.013 | 0.1936 | 0.031 | 0.555 | 0.608 | 0.348 | 0.793 | 0.046 |
| always_cheapest | all | 44934 | 0.165 | 0.2365 | 0.045 | 0.555 | 0.608 | 0.348 | 0.709 | 0.046 |
