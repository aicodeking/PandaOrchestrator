# Eval: `onnx:artifacts/panda-router-v2` on `gold` (n=359)

Sources: {'swe-rebench': 120, 'swe-smith': 25, 'wildchat': 214}  
Latency (batch 1): p50 27.836 ms, p95 171.894 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.641 / 0.794 / 0.095 |
| difficulty | MAE / Spearman / QWK / ECE | 0.897 / 0.705 / 0.594 / 0.072 |
| skills | mean MAE / mean Spearman / mean ECE | 0.712 / 0.638 / 0.127 |
| flags | F1 macro / AUROC macro / ECE | 0.584 / 0.886 / 0.043 |
| checklist | F1 macro / micro / AUROC | 0.502 / 0.724 / 0.879 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.238 / 0.716 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | 0.085 / 0.005 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 120 | 0.858 | 0.857 | 0.469 | 0.573 | 0.363 |
| swe-smith | 25 | 1.000 | 0.807 | 0.592 | 0.682 | 0.728 |
| wildchat | 214 | 0.477 | 0.931 | 0.656 | 0.215 | 0.377 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 17947 | 0.621 | 0.0274 | 0.592 | 0.826 | 0.260 | 0.536 | 0.575 | 0.000 |
| predicted | max_utility | 17947 | 0.890 | 0.0022 | 0.873 | 0.920 | 0.089 | 0.708 | 0.717 | 0.000 |
| predicted | max_quality | 17947 | 0.988 | 0.0008 | 1.002 | 0.953 | 0.040 | 0.796 | 0.796 | 0.000 |
| predicted | all | 53841 | 0.833 | 0.0101 | 0.917 | 0.900 | 0.130 | 0.680 | 0.696 | 0.000 |
| always_strongest | cheapest_above_threshold | 17947 | 0.170 | -0.0037 | 4.593 | 0.947 | 0.046 | 0.791 | 0.575 | 0.007 |
| always_strongest | max_utility | 17947 | 0.259 | 0.1086 | 3.003 | 0.947 | 0.046 | 0.791 | 0.717 | 0.007 |
| always_strongest | max_quality | 17947 | 0.965 | 0.0094 | 1.000 | 0.947 | 0.046 | 0.791 | 0.796 | 0.007 |
| always_strongest | all | 53841 | 0.465 | 0.0381 | 1.934 | 0.947 | 0.046 | 0.791 | 0.696 | 0.007 |
| always_cheapest | cheapest_above_threshold | 17947 | 0.271 | 0.2375 | 0.036 | 0.594 | 0.586 | 0.320 | 0.575 | 0.015 |
| always_cheapest | max_utility | 17947 | 0.076 | 0.3498 | 0.024 | 0.594 | 0.586 | 0.320 | 0.717 | 0.015 |
| always_cheapest | max_quality | 17947 | 0.012 | 0.2506 | 0.008 | 0.594 | 0.586 | 0.320 | 0.796 | 0.015 |
| always_cheapest | all | 53841 | 0.119 | 0.2793 | 0.015 | 0.594 | 0.586 | 0.320 | 0.696 | 0.015 |
