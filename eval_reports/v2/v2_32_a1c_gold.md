# Eval: `torch:checkpoints/v2_32_a1c/best` on `gold` (n=329)

Sources: {'swe-rebench': 109, 'swe-smith': 24, 'wildchat': 196}  
Latency (batch 1): p50 25.358 ms, p95 68.422 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.638 / 0.793 / 0.103 |
| difficulty | MAE / Spearman / QWK / ECE | 0.934 / 0.678 / 0.618 / 0.019 |
| skills | mean MAE / mean Spearman / mean ECE | 0.773 / 0.586 / 0.154 |
| flags | F1 macro / AUROC macro / ECE | 0.470 / 0.845 / 0.054 |
| checklist | F1 macro / micro / AUROC | 0.449 / 0.697 / 0.838 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.247 / 0.696 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | 0.132 / 0.004 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 109 | 0.844 | 0.875 | 0.385 | 0.455 | 0.311 |
| swe-smith | 24 | 1.000 | 0.750 | 0.594 | 0.636 | 0.642 |
| wildchat | 196 | 0.480 | 0.989 | 0.612 | 0.226 | 0.357 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 16446 | 0.624 | 0.0162 | 0.722 | 0.843 | 0.224 | 0.554 | 0.575 | 0.000 |
| predicted | max_utility | 16446 | 0.896 | 0.0023 | 0.907 | 0.925 | 0.072 | 0.716 | 0.720 | 0.000 |
| predicted | max_quality | 16446 | 0.989 | 0.0006 | 1.001 | 0.955 | 0.035 | 0.799 | 0.799 | 0.000 |
| predicted | all | 49338 | 0.836 | 0.0064 | 0.946 | 0.908 | 0.110 | 0.690 | 0.698 | 0.000 |
| always_strongest | cheapest_above_threshold | 16446 | 0.155 | -0.0019 | 5.186 | 0.949 | 0.040 | 0.794 | 0.575 | 0.007 |
| always_strongest | max_utility | 16446 | 0.247 | 0.1141 | 3.220 | 0.949 | 0.040 | 0.794 | 0.720 | 0.007 |
| always_strongest | max_quality | 16446 | 0.966 | 0.0090 | 0.999 | 0.949 | 0.040 | 0.794 | 0.799 | 0.007 |
| always_strongest | all | 49338 | 0.456 | 0.0404 | 1.994 | 0.949 | 0.040 | 0.794 | 0.698 | 0.007 |
| always_cheapest | cheapest_above_threshold | 16446 | 0.278 | 0.2377 | 0.042 | 0.606 | 0.569 | 0.325 | 0.575 | 0.016 |
| always_cheapest | max_utility | 16446 | 0.077 | 0.3536 | 0.026 | 0.606 | 0.569 | 0.325 | 0.720 | 0.016 |
| always_cheapest | max_quality | 16446 | 0.012 | 0.2486 | 0.008 | 0.606 | 0.569 | 0.325 | 0.799 | 0.016 |
| always_cheapest | all | 49338 | 0.122 | 0.2800 | 0.016 | 0.606 | 0.569 | 0.325 | 0.698 | 0.016 |
