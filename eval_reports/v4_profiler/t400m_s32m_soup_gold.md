# Eval: `onnx:artifacts/v4_candidates/t400m_s32m_soup` on `gold` (n=359)

Sources: {'swe-rebench': 120, 'swe-smith': 25, 'wildchat': 214}  
Latency (batch 1): p50 6.29 ms, p95 19.863 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.657 / 0.855 / 0.124 |
| difficulty | MAE / Spearman / QWK / ECE | 0.863 / 0.711 / 0.627 / 0.049 |
| skills | mean MAE / mean Spearman / mean ECE | 0.676 / 0.672 / 0.129 |
| flags | F1 macro / AUROC macro / ECE | 0.624 / 0.895 / 0.032 |
| checklist | F1 macro / micro / AUROC | 0.536 / 0.746 / 0.885 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.213 / 0.694 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | 0.015 / 0.005 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 120 | 0.842 | 0.807 | 0.441 | 0.635 | 0.370 |
| swe-smith | 25 | 1.000 | 0.572 | 0.776 | 0.721 | 0.867 |
| wildchat | 214 | 0.514 | 0.927 | 0.679 | 0.228 | 0.422 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 17947 | 0.623 | -0.0013 | 0.768 | 0.861 | 0.184 | 0.583 | 0.582 | 0.000 |
| predicted | max_utility | 17947 | 0.899 | 0.0021 | 0.898 | 0.925 | 0.079 | 0.716 | 0.720 | 0.000 |
| predicted | max_quality | 17947 | 0.986 | 0.0011 | 1.002 | 0.954 | 0.037 | 0.799 | 0.799 | 0.000 |
| predicted | all | 53841 | 0.836 | 0.0006 | 0.949 | 0.913 | 0.100 | 0.699 | 0.700 | 0.000 |
| always_strongest | cheapest_above_threshold | 17947 | 0.167 | 0.0018 | 4.798 | 0.948 | 0.043 | 0.794 | 0.582 | 0.007 |
| always_strongest | max_utility | 17947 | 0.257 | 0.1150 | 3.291 | 0.948 | 0.043 | 0.794 | 0.720 | 0.007 |
| always_strongest | max_quality | 17947 | 0.968 | 0.0102 | 0.996 | 0.948 | 0.043 | 0.794 | 0.799 | 0.007 |
| always_strongest | all | 53841 | 0.464 | 0.0423 | 1.978 | 0.948 | 0.043 | 0.794 | 0.700 | 0.007 |
| always_cheapest | cheapest_above_threshold | 17947 | 0.273 | 0.2457 | 0.039 | 0.595 | 0.583 | 0.322 | 0.582 | 0.015 |
| always_cheapest | max_utility | 17947 | 0.080 | 0.3589 | 0.026 | 0.595 | 0.583 | 0.322 | 0.720 | 0.015 |
| always_cheapest | max_quality | 17947 | 0.012 | 0.2541 | 0.008 | 0.595 | 0.583 | 0.322 | 0.799 | 0.015 |
| always_cheapest | all | 53841 | 0.122 | 0.2863 | 0.016 | 0.595 | 0.583 | 0.322 | 0.700 | 0.015 |
