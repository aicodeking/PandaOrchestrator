# Eval: `onnx:artifacts/v2_s32m` on `gold` (n=329)

Sources: {'swe-rebench': 109, 'swe-smith': 24, 'wildchat': 196}  
Latency (batch 1): p50 74.785 ms, p95 410.649 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.623 / 0.790 / 0.111 |
| difficulty | MAE / Spearman / QWK / ECE | 0.904 / 0.712 / 0.616 / 0.040 |
| skills | mean MAE / mean Spearman / mean ECE | 0.743 / 0.609 / 0.150 |
| flags | F1 macro / AUROC macro / ECE | 0.474 / 0.839 / 0.052 |
| checklist | F1 macro / micro / AUROC | 0.464 / 0.713 / 0.854 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.237 / 0.736 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | 0.085 / 0.004 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 109 | 0.853 | 0.836 | 0.484 | 0.462 | 0.348 |
| swe-smith | 24 | 1.000 | 0.755 | 0.619 | 0.636 | 0.652 |
| wildchat | 196 | 0.449 | 0.961 | 0.637 | 0.216 | 0.349 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 16446 | 0.641 | 0.0223 | 0.660 | 0.837 | 0.233 | 0.545 | 0.575 | 0.000 |
| predicted | max_utility | 16446 | 0.902 | 0.0017 | 0.892 | 0.925 | 0.072 | 0.714 | 0.720 | 0.000 |
| predicted | max_quality | 16446 | 0.989 | 0.0006 | 1.001 | 0.955 | 0.035 | 0.799 | 0.799 | 0.000 |
| predicted | all | 49338 | 0.844 | 0.0082 | 0.935 | 0.906 | 0.114 | 0.686 | 0.698 | 0.000 |
| always_strongest | cheapest_above_threshold | 16446 | 0.155 | -0.0019 | 5.186 | 0.949 | 0.040 | 0.794 | 0.575 | 0.007 |
| always_strongest | max_utility | 16446 | 0.247 | 0.1141 | 3.220 | 0.949 | 0.040 | 0.794 | 0.720 | 0.007 |
| always_strongest | max_quality | 16446 | 0.966 | 0.0090 | 0.999 | 0.949 | 0.040 | 0.794 | 0.799 | 0.007 |
| always_strongest | all | 49338 | 0.456 | 0.0404 | 1.994 | 0.949 | 0.040 | 0.794 | 0.698 | 0.007 |
| always_cheapest | cheapest_above_threshold | 16446 | 0.278 | 0.2377 | 0.042 | 0.606 | 0.569 | 0.325 | 0.575 | 0.016 |
| always_cheapest | max_utility | 16446 | 0.077 | 0.3536 | 0.026 | 0.606 | 0.569 | 0.325 | 0.720 | 0.016 |
| always_cheapest | max_quality | 16446 | 0.012 | 0.2486 | 0.008 | 0.606 | 0.569 | 0.325 | 0.799 | 0.016 |
| always_cheapest | all | 49338 | 0.122 | 0.2800 | 0.016 | 0.606 | 0.569 | 0.325 | 0.698 | 0.016 |
