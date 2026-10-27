# Eval: `onnx:artifacts/v4_candidates/t150m_s68m_seed0` on `gold` (n=359)

Sources: {'swe-rebench': 120, 'swe-smith': 25, 'wildchat': 214}  
Latency (batch 1): p50 13.14 ms, p95 41.59 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.685 / 0.880 / 0.088 |
| difficulty | MAE / Spearman / QWK / ECE | 0.839 / 0.729 / 0.674 / 0.051 |
| skills | mean MAE / mean Spearman / mean ECE | 0.643 / 0.695 / 0.123 |
| flags | F1 macro / AUROC macro / ECE | 0.664 / 0.910 / 0.027 |
| checklist | F1 macro / micro / AUROC | 0.572 / 0.762 / 0.900 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.216 / 0.685 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | 0.009 / 0.005 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 120 | 0.858 | 0.772 | 0.493 | 0.672 | 0.424 |
| swe-smith | 25 | 1.000 | 0.567 | 0.756 | 0.678 | 0.864 |
| wildchat | 214 | 0.551 | 0.908 | 0.689 | 0.283 | 0.464 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 17947 | 0.640 | -0.0016 | 0.907 | 0.866 | 0.173 | 0.588 | 0.582 | 0.000 |
| predicted | max_utility | 17947 | 0.902 | 0.0019 | 0.916 | 0.925 | 0.078 | 0.716 | 0.720 | 0.000 |
| predicted | max_quality | 17947 | 0.985 | 0.0011 | 1.002 | 0.954 | 0.037 | 0.799 | 0.799 | 0.000 |
| predicted | all | 53841 | 0.843 | 0.0005 | 0.972 | 0.915 | 0.096 | 0.701 | 0.700 | 0.000 |
| always_strongest | cheapest_above_threshold | 17947 | 0.167 | 0.0018 | 4.798 | 0.948 | 0.043 | 0.794 | 0.582 | 0.007 |
| always_strongest | max_utility | 17947 | 0.257 | 0.1150 | 3.291 | 0.948 | 0.043 | 0.794 | 0.720 | 0.007 |
| always_strongest | max_quality | 17947 | 0.968 | 0.0102 | 0.996 | 0.948 | 0.043 | 0.794 | 0.799 | 0.007 |
| always_strongest | all | 53841 | 0.464 | 0.0423 | 1.978 | 0.948 | 0.043 | 0.794 | 0.700 | 0.007 |
| always_cheapest | cheapest_above_threshold | 17947 | 0.273 | 0.2457 | 0.039 | 0.595 | 0.583 | 0.322 | 0.582 | 0.015 |
| always_cheapest | max_utility | 17947 | 0.080 | 0.3589 | 0.026 | 0.595 | 0.583 | 0.322 | 0.720 | 0.015 |
| always_cheapest | max_quality | 17947 | 0.012 | 0.2541 | 0.008 | 0.595 | 0.583 | 0.322 | 0.799 | 0.015 |
| always_cheapest | all | 53841 | 0.122 | 0.2863 | 0.016 | 0.595 | 0.583 | 0.322 | 0.700 | 0.015 |
