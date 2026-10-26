# Eval: `onnx:artifacts/v2_t150m` on `gold` (n=329)

Sources: {'swe-rebench': 109, 'swe-smith': 24, 'wildchat': 196}  
Latency (batch 1): p50 51.846 ms, p95 238.75 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.675 / 0.845 / 0.100 |
| difficulty | MAE / Spearman / QWK / ECE | 0.867 / 0.721 / 0.655 / 0.043 |
| skills | mean MAE / mean Spearman / mean ECE | 0.693 / 0.638 / 0.150 |
| flags | F1 macro / AUROC macro / ECE | 0.466 / 0.849 / 0.043 |
| checklist | F1 macro / micro / AUROC | 0.506 / 0.731 / 0.877 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.221 / 0.723 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | 0.207 / 0.004 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 109 | 0.862 | 0.853 | 0.413 | 0.437 | 0.349 |
| swe-smith | 24 | 1.000 | 0.598 | 0.691 | 0.509 | 0.674 |
| wildchat | 196 | 0.531 | 0.908 | 0.669 | 0.215 | 0.419 |

## Routing (cards: cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 16446 | 0.650 | 0.0253 | 0.669 | 0.835 | 0.236 | 0.541 | 0.575 | 0.000 |
| predicted | max_utility | 16446 | 0.908 | 0.0015 | 0.900 | 0.926 | 0.071 | 0.715 | 0.720 | 0.000 |
| predicted | max_quality | 16446 | 0.990 | 0.0005 | 1.001 | 0.955 | 0.035 | 0.799 | 0.799 | 0.000 |
| predicted | all | 49338 | 0.849 | 0.0091 | 0.938 | 0.905 | 0.114 | 0.685 | 0.698 | 0.000 |
| always_strongest | cheapest_above_threshold | 16446 | 0.155 | -0.0019 | 5.186 | 0.949 | 0.040 | 0.794 | 0.575 | 0.007 |
| always_strongest | max_utility | 16446 | 0.247 | 0.1141 | 3.220 | 0.949 | 0.040 | 0.794 | 0.720 | 0.007 |
| always_strongest | max_quality | 16446 | 0.966 | 0.0090 | 0.999 | 0.949 | 0.040 | 0.794 | 0.799 | 0.007 |
| always_strongest | all | 49338 | 0.456 | 0.0404 | 1.994 | 0.949 | 0.040 | 0.794 | 0.698 | 0.007 |
| always_cheapest | cheapest_above_threshold | 16446 | 0.278 | 0.2377 | 0.042 | 0.606 | 0.569 | 0.325 | 0.575 | 0.016 |
| always_cheapest | max_utility | 16446 | 0.077 | 0.3536 | 0.026 | 0.606 | 0.569 | 0.325 | 0.720 | 0.016 |
| always_cheapest | max_quality | 16446 | 0.012 | 0.2486 | 0.008 | 0.606 | 0.569 | 0.325 | 0.799 | 0.016 |
| always_cheapest | all | 49338 | 0.122 | 0.2800 | 0.016 | 0.606 | 0.569 | 0.325 | 0.698 | 0.016 |
