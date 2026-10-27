# Eval: `onnx:artifacts/v4_candidates/t150m_s32m_soup` on `gold` (n=359)

Sources: {'swe-rebench': 120, 'swe-smith': 25, 'wildchat': 214}  
Latency (batch 1): p50 9.61 ms, p95 45.396 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.682 / 0.855 / 0.084 |
| difficulty | MAE / Spearman / QWK / ECE | 0.856 / 0.721 / 0.656 / 0.030 |
| skills | mean MAE / mean Spearman / mean ECE | 0.666 / 0.680 / 0.134 |
| flags | F1 macro / AUROC macro / ECE | 0.643 / 0.897 / 0.032 |
| checklist | F1 macro / micro / AUROC | 0.562 / 0.749 / 0.889 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.216 / 0.660 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | -0.033 / 0.005 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 120 | 0.875 | 0.769 | 0.546 | 0.649 | 0.396 |
| swe-smith | 25 | 1.000 | 0.604 | 0.771 | 0.713 | 0.830 |
| wildchat | 214 | 0.537 | 0.935 | 0.673 | 0.311 | 0.453 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 17947 | 0.621 | -0.0049 | 0.825 | 0.866 | 0.173 | 0.590 | 0.582 | 0.000 |
| predicted | max_utility | 17947 | 0.901 | 0.0021 | 0.911 | 0.926 | 0.077 | 0.717 | 0.720 | 0.000 |
| predicted | max_quality | 17947 | 0.987 | 0.0010 | 1.001 | 0.954 | 0.037 | 0.799 | 0.799 | 0.000 |
| predicted | all | 53841 | 0.836 | -0.0006 | 0.959 | 0.915 | 0.096 | 0.702 | 0.700 | 0.000 |
| always_strongest | cheapest_above_threshold | 17947 | 0.167 | 0.0018 | 4.798 | 0.948 | 0.043 | 0.794 | 0.582 | 0.007 |
| always_strongest | max_utility | 17947 | 0.257 | 0.1150 | 3.291 | 0.948 | 0.043 | 0.794 | 0.720 | 0.007 |
| always_strongest | max_quality | 17947 | 0.968 | 0.0102 | 0.996 | 0.948 | 0.043 | 0.794 | 0.799 | 0.007 |
| always_strongest | all | 53841 | 0.464 | 0.0423 | 1.978 | 0.948 | 0.043 | 0.794 | 0.700 | 0.007 |
| always_cheapest | cheapest_above_threshold | 17947 | 0.273 | 0.2457 | 0.039 | 0.595 | 0.583 | 0.322 | 0.582 | 0.015 |
| always_cheapest | max_utility | 17947 | 0.080 | 0.3589 | 0.026 | 0.595 | 0.583 | 0.322 | 0.720 | 0.015 |
| always_cheapest | max_quality | 17947 | 0.012 | 0.2541 | 0.008 | 0.595 | 0.583 | 0.322 | 0.799 | 0.015 |
| always_cheapest | all | 53841 | 0.122 | 0.2863 | 0.016 | 0.595 | 0.583 | 0.322 | 0.700 | 0.015 |
