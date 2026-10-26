# Eval: `torch:checkpoints/v2_32_a03c/best` on `gold` (n=329)

Sources: {'swe-rebench': 109, 'swe-smith': 24, 'wildchat': 196}  
Latency (batch 1): p50 12.38 ms, p95 22.739 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.635 / 0.812 / 0.110 |
| difficulty | MAE / Spearman / QWK / ECE | 0.911 / 0.706 / 0.623 / 0.029 |
| skills | mean MAE / mean Spearman / mean ECE | 0.738 / 0.609 / 0.151 |
| flags | F1 macro / AUROC macro / ECE | 0.485 / 0.839 / 0.051 |
| checklist | F1 macro / micro / AUROC | 0.474 / 0.717 / 0.849 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.237 / 0.754 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | 0.090 / 0.004 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 109 | 0.872 | 0.898 | 0.436 | 0.461 | 0.360 |
| swe-smith | 24 | 1.000 | 0.709 | 0.620 | 0.636 | 0.642 |
| wildchat | 196 | 0.459 | 0.943 | 0.644 | 0.230 | 0.378 |

## Routing (cards: cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 16446 | 0.643 | 0.0192 | 0.706 | 0.841 | 0.224 | 0.550 | 0.575 | 0.000 |
| predicted | max_utility | 16446 | 0.901 | 0.0018 | 0.903 | 0.926 | 0.072 | 0.715 | 0.720 | 0.000 |
| predicted | max_quality | 16446 | 0.989 | 0.0006 | 1.001 | 0.955 | 0.035 | 0.799 | 0.799 | 0.000 |
| predicted | all | 49338 | 0.844 | 0.0072 | 0.943 | 0.907 | 0.110 | 0.688 | 0.698 | 0.000 |
| always_strongest | cheapest_above_threshold | 16446 | 0.155 | -0.0019 | 5.186 | 0.949 | 0.040 | 0.794 | 0.575 | 0.007 |
| always_strongest | max_utility | 16446 | 0.247 | 0.1141 | 3.220 | 0.949 | 0.040 | 0.794 | 0.720 | 0.007 |
| always_strongest | max_quality | 16446 | 0.966 | 0.0090 | 0.999 | 0.949 | 0.040 | 0.794 | 0.799 | 0.007 |
| always_strongest | all | 49338 | 0.456 | 0.0404 | 1.994 | 0.949 | 0.040 | 0.794 | 0.698 | 0.007 |
| always_cheapest | cheapest_above_threshold | 16446 | 0.278 | 0.2377 | 0.042 | 0.606 | 0.569 | 0.325 | 0.575 | 0.016 |
| always_cheapest | max_utility | 16446 | 0.077 | 0.3536 | 0.026 | 0.606 | 0.569 | 0.325 | 0.720 | 0.016 |
| always_cheapest | max_quality | 16446 | 0.012 | 0.2486 | 0.008 | 0.606 | 0.569 | 0.325 | 0.799 | 0.016 |
| always_cheapest | all | 49338 | 0.122 | 0.2800 | 0.016 | 0.606 | 0.569 | 0.325 | 0.698 | 0.016 |
