# Eval: `heuristic` on `gold` (n=329)

Sources: {'swe-rebench': 109, 'swe-smith': 24, 'wildchat': 196}  
Latency (batch 1): p50 0.378 ms, p95 2.283 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.492 / 0.660 / 0.207 |
| difficulty | MAE / Spearman / QWK / ECE | 1.374 / 0.508 / 0.327 / 0.157 |
| skills | mean MAE / mean Spearman / mean ECE | 1.241 / 0.289 / 0.270 |
| flags | F1 macro / AUROC macro / ECE | 0.252 / 0.641 / 0.128 |
| checklist | F1 macro / micro / AUROC | 0.233 / 0.357 / 0.667 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.285 / 0.830 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | -0.015 / 0.004 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 109 | 0.532 | 1.828 | 0.339 | 0.330 | 0.214 |
| swe-smith | 24 | 0.708 | 1.511 | 0.373 | 0.333 | 0.284 |
| wildchat | 196 | 0.444 | 1.105 | 0.526 | 0.087 | 0.171 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 16446 | 0.539 | 0.1134 | 0.320 | 0.731 | 0.424 | 0.435 | 0.575 | 0.001 |
| predicted | max_utility | 16446 | 0.863 | 0.0053 | 0.770 | 0.917 | 0.088 | 0.702 | 0.720 | 0.001 |
| predicted | max_quality | 16446 | 0.981 | 0.0011 | 1.000 | 0.954 | 0.036 | 0.798 | 0.799 | 0.001 |
| predicted | all | 49338 | 0.794 | 0.0399 | 0.865 | 0.867 | 0.182 | 0.645 | 0.698 | 0.001 |
| always_strongest | cheapest_above_threshold | 16446 | 0.155 | -0.0019 | 5.186 | 0.949 | 0.040 | 0.794 | 0.575 | 0.007 |
| always_strongest | max_utility | 16446 | 0.247 | 0.1141 | 3.220 | 0.949 | 0.040 | 0.794 | 0.720 | 0.007 |
| always_strongest | max_quality | 16446 | 0.966 | 0.0090 | 0.999 | 0.949 | 0.040 | 0.794 | 0.799 | 0.007 |
| always_strongest | all | 49338 | 0.456 | 0.0404 | 1.994 | 0.949 | 0.040 | 0.794 | 0.698 | 0.007 |
| always_cheapest | cheapest_above_threshold | 16446 | 0.278 | 0.2377 | 0.042 | 0.606 | 0.569 | 0.325 | 0.575 | 0.016 |
| always_cheapest | max_utility | 16446 | 0.077 | 0.3536 | 0.026 | 0.606 | 0.569 | 0.325 | 0.720 | 0.016 |
| always_cheapest | max_quality | 16446 | 0.012 | 0.2486 | 0.008 | 0.606 | 0.569 | 0.325 | 0.799 | 0.016 |
| always_cheapest | all | 49338 | 0.122 | 0.2800 | 0.016 | 0.606 | 0.569 | 0.325 | 0.698 | 0.016 |
