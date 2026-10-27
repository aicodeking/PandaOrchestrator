# Eval: `onnx:artifacts/v4_candidates/t400m_s68m_seed0` on `gold` (n=359)

Sources: {'swe-rebench': 120, 'swe-smith': 25, 'wildchat': 214}  
Latency (batch 1): p50 13.261 ms, p95 41.374 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.688 / 0.877 / 0.097 |
| difficulty | MAE / Spearman / QWK / ECE | 0.856 / 0.728 / 0.677 / 0.036 |
| skills | mean MAE / mean Spearman / mean ECE | 0.663 / 0.688 / 0.136 |
| flags | F1 macro / AUROC macro / ECE | 0.648 / 0.910 / 0.032 |
| checklist | F1 macro / micro / AUROC | 0.542 / 0.754 / 0.894 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.214 / 0.705 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | 0.085 / 0.005 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 120 | 0.867 | 0.763 | 0.471 | 0.616 | 0.377 |
| swe-smith | 25 | 1.000 | 0.565 | 0.745 | 0.688 | 0.804 |
| wildchat | 214 | 0.551 | 0.942 | 0.682 | 0.283 | 0.436 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 17947 | 0.630 | -0.0078 | 0.954 | 0.871 | 0.163 | 0.595 | 0.582 | 0.000 |
| predicted | max_utility | 17947 | 0.901 | 0.0019 | 0.927 | 0.926 | 0.077 | 0.717 | 0.720 | 0.000 |
| predicted | max_quality | 17947 | 0.985 | 0.0011 | 1.002 | 0.954 | 0.037 | 0.799 | 0.799 | 0.000 |
| predicted | all | 53841 | 0.839 | -0.0016 | 0.980 | 0.917 | 0.093 | 0.704 | 0.700 | 0.000 |
| always_strongest | cheapest_above_threshold | 17947 | 0.167 | 0.0018 | 4.798 | 0.948 | 0.043 | 0.794 | 0.582 | 0.007 |
| always_strongest | max_utility | 17947 | 0.257 | 0.1150 | 3.291 | 0.948 | 0.043 | 0.794 | 0.720 | 0.007 |
| always_strongest | max_quality | 17947 | 0.968 | 0.0102 | 0.996 | 0.948 | 0.043 | 0.794 | 0.799 | 0.007 |
| always_strongest | all | 53841 | 0.464 | 0.0423 | 1.978 | 0.948 | 0.043 | 0.794 | 0.700 | 0.007 |
| always_cheapest | cheapest_above_threshold | 17947 | 0.273 | 0.2457 | 0.039 | 0.595 | 0.583 | 0.322 | 0.582 | 0.015 |
| always_cheapest | max_utility | 17947 | 0.080 | 0.3589 | 0.026 | 0.595 | 0.583 | 0.322 | 0.720 | 0.015 |
| always_cheapest | max_quality | 17947 | 0.012 | 0.2541 | 0.008 | 0.595 | 0.583 | 0.322 | 0.799 | 0.015 |
| always_cheapest | all | 53841 | 0.122 | 0.2863 | 0.016 | 0.595 | 0.583 | 0.322 | 0.700 | 0.015 |
