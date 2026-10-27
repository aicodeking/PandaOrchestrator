# Eval: `onnx:artifacts/panda-router-v3` on `gold` (n=359)

Sources: {'swe-rebench': 120, 'swe-smith': 25, 'wildchat': 214}  
Latency (batch 1): p50 7.62 ms, p95 27.576 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.688 / 0.844 / 0.080 |
| difficulty | MAE / Spearman / QWK / ECE | 0.825 / 0.747 / 0.666 / 0.041 |
| skills | mean MAE / mean Spearman / mean ECE | 0.681 / 0.676 / 0.136 |
| flags | F1 macro / AUROC macro / ECE | 0.639 / 0.901 / 0.029 |
| checklist | F1 macro / micro / AUROC | 0.541 / 0.754 / 0.893 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.212 / 0.713 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | 0.090 / 0.005 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 120 | 0.867 | 0.816 | 0.512 | 0.598 | 0.386 |
| swe-smith | 25 | 1.000 | 0.659 | 0.721 | 0.656 | 0.785 |
| wildchat | 214 | 0.551 | 0.850 | 0.717 | 0.307 | 0.440 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 17947 | 0.637 | 0.0155 | 0.720 | 0.842 | 0.224 | 0.554 | 0.575 | 0.000 |
| predicted | max_utility | 17947 | 0.897 | 0.0021 | 0.901 | 0.922 | 0.085 | 0.710 | 0.717 | 0.000 |
| predicted | max_quality | 17947 | 0.988 | 0.0006 | 1.002 | 0.953 | 0.040 | 0.796 | 0.796 | 0.000 |
| predicted | all | 53841 | 0.841 | 0.0060 | 0.940 | 0.905 | 0.116 | 0.687 | 0.696 | 0.000 |
| always_strongest | cheapest_above_threshold | 17947 | 0.170 | -0.0037 | 4.593 | 0.947 | 0.046 | 0.791 | 0.575 | 0.007 |
| always_strongest | max_utility | 17947 | 0.259 | 0.1086 | 3.003 | 0.947 | 0.046 | 0.791 | 0.717 | 0.007 |
| always_strongest | max_quality | 17947 | 0.965 | 0.0094 | 1.000 | 0.947 | 0.046 | 0.791 | 0.796 | 0.007 |
| always_strongest | all | 53841 | 0.465 | 0.0381 | 1.934 | 0.947 | 0.046 | 0.791 | 0.696 | 0.007 |
| always_cheapest | cheapest_above_threshold | 17947 | 0.271 | 0.2375 | 0.036 | 0.594 | 0.586 | 0.320 | 0.575 | 0.015 |
| always_cheapest | max_utility | 17947 | 0.076 | 0.3498 | 0.024 | 0.594 | 0.586 | 0.320 | 0.717 | 0.015 |
| always_cheapest | max_quality | 17947 | 0.012 | 0.2506 | 0.008 | 0.594 | 0.586 | 0.320 | 0.796 | 0.015 |
| always_cheapest | all | 53841 | 0.119 | 0.2793 | 0.015 | 0.594 | 0.586 | 0.320 | 0.696 | 0.015 |
