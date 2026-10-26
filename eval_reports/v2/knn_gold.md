# Eval: `knn` on `gold` (n=329)

Sources: {'swe-rebench': 109, 'swe-smith': 24, 'wildchat': 196}  
Latency (batch 1): p50 13.15 ms, p95 23.169 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.562 / 0.702 / 0.113 |
| difficulty | MAE / Spearman / QWK / ECE | 1.190 / 0.461 / 0.425 / 0.034 |
| skills | mean MAE / mean Spearman / mean ECE | 1.020 / 0.440 / 0.160 |
| flags | F1 macro / AUROC macro / ECE | 0.369 / 0.710 / 0.097 |
| checklist | F1 macro / micro / AUROC | 0.413 / 0.664 / 0.746 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.318 / 0.796 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | 0.088 / 0.004 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 109 | 0.807 | 0.845 | 0.164 | 0.348 | 0.319 |
| swe-smith | 24 | 1.000 | 0.812 | 0.197 | 0.389 | 0.503 |
| wildchat | 196 | 0.372 | 1.429 | 0.435 | 0.225 | 0.330 |

## Routing (cards: cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 16446 | 0.518 | -0.0295 | 1.169 | 0.888 | 0.135 | 0.632 | 0.575 | 0.000 |
| predicted | max_utility | 16446 | 0.870 | 0.0041 | 1.004 | 0.929 | 0.066 | 0.725 | 0.720 | 0.000 |
| predicted | max_quality | 16446 | 0.987 | 0.0009 | 1.002 | 0.955 | 0.035 | 0.799 | 0.799 | 0.000 |
| predicted | all | 49338 | 0.792 | -0.0082 | 1.024 | 0.924 | 0.079 | 0.719 | 0.698 | 0.000 |
| always_strongest | cheapest_above_threshold | 16446 | 0.155 | -0.0019 | 5.186 | 0.949 | 0.040 | 0.794 | 0.575 | 0.007 |
| always_strongest | max_utility | 16446 | 0.247 | 0.1141 | 3.220 | 0.949 | 0.040 | 0.794 | 0.720 | 0.007 |
| always_strongest | max_quality | 16446 | 0.966 | 0.0090 | 0.999 | 0.949 | 0.040 | 0.794 | 0.799 | 0.007 |
| always_strongest | all | 49338 | 0.456 | 0.0404 | 1.994 | 0.949 | 0.040 | 0.794 | 0.698 | 0.007 |
| always_cheapest | cheapest_above_threshold | 16446 | 0.278 | 0.2377 | 0.042 | 0.606 | 0.569 | 0.325 | 0.575 | 0.016 |
| always_cheapest | max_utility | 16446 | 0.077 | 0.3536 | 0.026 | 0.606 | 0.569 | 0.325 | 0.720 | 0.016 |
| always_cheapest | max_quality | 16446 | 0.012 | 0.2486 | 0.008 | 0.606 | 0.569 | 0.325 | 0.799 | 0.016 |
| always_cheapest | all | 49338 | 0.122 | 0.2800 | 0.016 | 0.606 | 0.569 | 0.325 | 0.698 | 0.016 |
