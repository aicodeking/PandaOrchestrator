# Eval: `onnx:artifacts/v3_32_a10_onnx` on `gold` (n=359)

Sources: {'swe-rebench': 120, 'swe-smith': 25, 'wildchat': 214}  
Latency (batch 1): p50 6.27 ms, p95 20.093 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.652 / 0.825 / 0.113 |
| difficulty | MAE / Spearman / QWK / ECE | 1.032 / 0.549 / 0.508 / 0.011 |
| skills | mean MAE / mean Spearman / mean ECE | 0.697 / 0.643 / 0.125 |
| flags | F1 macro / AUROC macro / ECE | 0.605 / 0.890 / 0.039 |
| checklist | F1 macro / micro / AUROC | 0.509 / 0.733 / 0.872 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.226 / 0.719 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | 0.087 / 0.005 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 120 | 0.825 | 0.913 | 0.385 | 0.582 | 0.355 |
| swe-smith | 25 | 1.000 | 0.819 | 0.536 | 0.711 | 0.756 |
| wildchat | 214 | 0.514 | 1.124 | 0.609 | 0.289 | 0.398 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 17947 | 0.520 | -0.0086 | 0.796 | 0.860 | 0.199 | 0.594 | 0.575 | 0.000 |
| predicted | max_utility | 17947 | 0.875 | 0.0028 | 0.898 | 0.921 | 0.088 | 0.712 | 0.717 | 0.000 |
| predicted | max_quality | 17947 | 0.987 | 0.0007 | 1.002 | 0.953 | 0.040 | 0.796 | 0.796 | 0.000 |
| predicted | all | 53841 | 0.794 | -0.0017 | 0.951 | 0.911 | 0.109 | 0.701 | 0.696 | 0.000 |
| always_strongest | cheapest_above_threshold | 17947 | 0.170 | -0.0037 | 4.593 | 0.947 | 0.046 | 0.791 | 0.575 | 0.007 |
| always_strongest | max_utility | 17947 | 0.259 | 0.1086 | 3.003 | 0.947 | 0.046 | 0.791 | 0.717 | 0.007 |
| always_strongest | max_quality | 17947 | 0.965 | 0.0094 | 1.000 | 0.947 | 0.046 | 0.791 | 0.796 | 0.007 |
| always_strongest | all | 53841 | 0.465 | 0.0381 | 1.934 | 0.947 | 0.046 | 0.791 | 0.696 | 0.007 |
| always_cheapest | cheapest_above_threshold | 17947 | 0.271 | 0.2375 | 0.036 | 0.594 | 0.586 | 0.320 | 0.575 | 0.015 |
| always_cheapest | max_utility | 17947 | 0.076 | 0.3498 | 0.024 | 0.594 | 0.586 | 0.320 | 0.717 | 0.015 |
| always_cheapest | max_quality | 17947 | 0.012 | 0.2506 | 0.008 | 0.594 | 0.586 | 0.320 | 0.796 | 0.015 |
| always_cheapest | all | 53841 | 0.119 | 0.2793 | 0.015 | 0.594 | 0.586 | 0.320 | 0.696 | 0.015 |
