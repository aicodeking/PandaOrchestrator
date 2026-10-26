# Eval: `fixed_average` on `gold` (n=329)

Sources: {'swe-rebench': 109, 'swe-smith': 24, 'wildchat': 196}  
Latency (batch 1): p50 0.0 ms, p95 0.0 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.353 / 0.486 / 0.008 |
| difficulty | MAE / Spearman / QWK / ECE | 1.760 / - / 0.000 / 0.030 |
| skills | mean MAE / mean Spearman / mean ECE | 1.804 / - / 0.271 |
| flags | F1 macro / AUROC macro / ECE | 0.318 / 0.500 / 0.171 |
| checklist | F1 macro / micro / AUROC | 0.190 / 0.537 / 0.500 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.428 / 0.699 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | - / 0.004 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 109 | 0.771 | 0.878 | - | 0.443 | 0.251 |
| swe-smith | 24 | 1.000 | 1.117 | - | 0.370 | 0.371 |
| wildchat | 196 | 0.041 | 2.330 | - | 0.223 | 0.134 |

## Routing (cards: cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 16446 | 0.262 | -0.0742 | 2.111 | 0.942 | 0.043 | 0.755 | 0.575 | 0.000 |
| predicted | max_utility | 16446 | 0.817 | 0.0071 | 1.083 | 0.933 | 0.061 | 0.737 | 0.720 | 0.000 |
| predicted | max_quality | 16446 | 0.979 | 0.0017 | 1.002 | 0.955 | 0.035 | 0.799 | 0.799 | 0.000 |
| predicted | all | 49338 | 0.686 | -0.0218 | 1.161 | 0.943 | 0.046 | 0.764 | 0.698 | 0.000 |
| always_strongest | cheapest_above_threshold | 16446 | 0.155 | -0.0019 | 5.186 | 0.949 | 0.040 | 0.794 | 0.575 | 0.007 |
| always_strongest | max_utility | 16446 | 0.247 | 0.1141 | 3.220 | 0.949 | 0.040 | 0.794 | 0.720 | 0.007 |
| always_strongest | max_quality | 16446 | 0.966 | 0.0090 | 0.999 | 0.949 | 0.040 | 0.794 | 0.799 | 0.007 |
| always_strongest | all | 49338 | 0.456 | 0.0404 | 1.994 | 0.949 | 0.040 | 0.794 | 0.698 | 0.007 |
| always_cheapest | cheapest_above_threshold | 16446 | 0.278 | 0.2377 | 0.042 | 0.606 | 0.569 | 0.325 | 0.575 | 0.016 |
| always_cheapest | max_utility | 16446 | 0.077 | 0.3536 | 0.026 | 0.606 | 0.569 | 0.325 | 0.720 | 0.016 |
| always_cheapest | max_quality | 16446 | 0.012 | 0.2486 | 0.008 | 0.606 | 0.569 | 0.325 | 0.799 | 0.016 |
| always_cheapest | all | 49338 | 0.122 | 0.2800 | 0.016 | 0.606 | 0.569 | 0.325 | 0.698 | 0.016 |
