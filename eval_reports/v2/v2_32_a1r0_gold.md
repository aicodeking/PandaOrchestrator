# Eval: `torch:checkpoints/v2_32_a1r0/best` on `gold` (n=329)

Sources: {'swe-rebench': 109, 'swe-smith': 24, 'wildchat': 196}  
Latency (batch 1): p50 390.463 ms, p95 1160.357 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.641 / 0.793 / 0.104 |
| difficulty | MAE / Spearman / QWK / ECE | 0.924 / 0.683 / 0.608 / 0.015 |
| skills | mean MAE / mean Spearman / mean ECE | 0.762 / 0.600 / 0.155 |
| flags | F1 macro / AUROC macro / ECE | 0.472 / 0.857 / 0.059 |
| checklist | F1 macro / micro / AUROC | 0.463 / 0.718 / 0.847 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.243 / 0.717 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | 0.121 / 0.004 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 109 | 0.853 | 0.892 | 0.282 | 0.446 | 0.337 |
| swe-smith | 24 | 1.000 | 0.758 | 0.509 | 0.636 | 0.644 |
| wildchat | 196 | 0.480 | 0.962 | 0.623 | 0.219 | 0.355 |

## Routing (cards: cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 16446 | 0.628 | 0.0162 | 0.704 | 0.843 | 0.221 | 0.554 | 0.575 | 0.000 |
| predicted | max_utility | 16446 | 0.900 | 0.0021 | 0.909 | 0.925 | 0.072 | 0.716 | 0.720 | 0.000 |
| predicted | max_quality | 16446 | 0.989 | 0.0005 | 1.001 | 0.955 | 0.035 | 0.799 | 0.799 | 0.000 |
| predicted | all | 49338 | 0.839 | 0.0063 | 0.944 | 0.908 | 0.109 | 0.689 | 0.698 | 0.000 |
| always_strongest | cheapest_above_threshold | 16446 | 0.155 | -0.0019 | 5.186 | 0.949 | 0.040 | 0.794 | 0.575 | 0.007 |
| always_strongest | max_utility | 16446 | 0.247 | 0.1141 | 3.220 | 0.949 | 0.040 | 0.794 | 0.720 | 0.007 |
| always_strongest | max_quality | 16446 | 0.966 | 0.0090 | 0.999 | 0.949 | 0.040 | 0.794 | 0.799 | 0.007 |
| always_strongest | all | 49338 | 0.456 | 0.0404 | 1.994 | 0.949 | 0.040 | 0.794 | 0.698 | 0.007 |
| always_cheapest | cheapest_above_threshold | 16446 | 0.278 | 0.2377 | 0.042 | 0.606 | 0.569 | 0.325 | 0.575 | 0.016 |
| always_cheapest | max_utility | 16446 | 0.077 | 0.3536 | 0.026 | 0.606 | 0.569 | 0.325 | 0.720 | 0.016 |
| always_cheapest | max_quality | 16446 | 0.012 | 0.2486 | 0.008 | 0.606 | 0.569 | 0.325 | 0.799 | 0.016 |
| always_cheapest | all | 49338 | 0.122 | 0.2800 | 0.016 | 0.606 | 0.569 | 0.325 | 0.698 | 0.016 |
