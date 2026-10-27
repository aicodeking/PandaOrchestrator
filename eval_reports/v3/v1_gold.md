# Eval: `onnx:artifacts/panda-router-v1` on `gold` (n=359)

Sources: {'swe-rebench': 120, 'swe-smith': 25, 'wildchat': 214}  
Latency (batch 1): p50 37.443 ms, p95 223.185 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.624 / 0.780 / 0.146 |
| difficulty | MAE / Spearman / QWK / ECE | 0.900 / 0.675 / 0.613 / 0.030 |
| skills | mean MAE / mean Spearman / mean ECE | 0.755 / 0.610 / 0.126 |
| flags | F1 macro / AUROC macro / ECE | 0.608 / 0.885 / 0.040 |
| checklist | F1 macro / micro / AUROC | 0.438 / 0.716 / 0.838 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.248 / 0.721 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | -0.019 / 0.005 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 120 | 0.842 | 0.807 | 0.464 | 0.588 | 0.351 |
| swe-smith | 25 | 1.000 | 0.804 | 0.612 | 0.790 | 0.756 |
| wildchat | 214 | 0.458 | 0.963 | 0.622 | 0.199 | 0.305 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 17947 | 0.608 | 0.0134 | 0.712 | 0.841 | 0.226 | 0.556 | 0.575 | 0.000 |
| predicted | max_utility | 17947 | 0.887 | 0.0025 | 0.896 | 0.921 | 0.087 | 0.710 | 0.717 | 0.000 |
| predicted | max_quality | 17947 | 0.986 | 0.0008 | 1.002 | 0.953 | 0.040 | 0.796 | 0.796 | 0.000 |
| predicted | all | 53841 | 0.827 | 0.0056 | 0.939 | 0.905 | 0.118 | 0.688 | 0.696 | 0.000 |
| always_strongest | cheapest_above_threshold | 17947 | 0.170 | -0.0037 | 4.593 | 0.947 | 0.046 | 0.791 | 0.575 | 0.007 |
| always_strongest | max_utility | 17947 | 0.259 | 0.1086 | 3.003 | 0.947 | 0.046 | 0.791 | 0.717 | 0.007 |
| always_strongest | max_quality | 17947 | 0.965 | 0.0094 | 1.000 | 0.947 | 0.046 | 0.791 | 0.796 | 0.007 |
| always_strongest | all | 53841 | 0.465 | 0.0381 | 1.934 | 0.947 | 0.046 | 0.791 | 0.696 | 0.007 |
| always_cheapest | cheapest_above_threshold | 17947 | 0.271 | 0.2375 | 0.036 | 0.594 | 0.586 | 0.320 | 0.575 | 0.015 |
| always_cheapest | max_utility | 17947 | 0.076 | 0.3498 | 0.024 | 0.594 | 0.586 | 0.320 | 0.717 | 0.015 |
| always_cheapest | max_quality | 17947 | 0.012 | 0.2506 | 0.008 | 0.594 | 0.586 | 0.320 | 0.796 | 0.015 |
| always_cheapest | all | 53841 | 0.119 | 0.2793 | 0.015 | 0.594 | 0.586 | 0.320 | 0.696 | 0.015 |
