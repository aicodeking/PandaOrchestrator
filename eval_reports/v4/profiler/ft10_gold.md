# Eval: `onnx:/tmp/v4ft` on `gold` (n=359)

Sources: {'swe-rebench': 120, 'swe-smith': 25, 'wildchat': 214}  
Latency (batch 1): p50 12.807 ms, p95 68.644 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.685 / 0.850 / 0.086 |
| difficulty | MAE / Spearman / QWK / ECE | 0.873 / 0.710 / 0.637 / 0.056 |
| skills | mean MAE / mean Spearman / mean ECE | 0.650 / 0.680 / 0.135 |
| flags | F1 macro / AUROC macro / ECE | 0.635 / 0.895 / 0.030 |
| checklist | F1 macro / micro / AUROC | 0.553 / 0.749 / 0.892 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.210 / 0.682 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | -0.047 / 0.005 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 120 | 0.867 | 0.783 | 0.522 | 0.643 | 0.384 |
| swe-smith | 25 | 1.000 | 0.630 | 0.694 | 0.713 | 0.828 |
| wildchat | 214 | 0.547 | 0.952 | 0.669 | 0.276 | 0.450 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 17947 | 0.609 | -0.0062 | 0.931 | 0.869 | 0.170 | 0.595 | 0.582 | 0.000 |
| predicted | max_utility | 17947 | 0.899 | 0.0022 | 0.916 | 0.926 | 0.076 | 0.718 | 0.720 | 0.000 |
| predicted | max_quality | 17947 | 0.986 | 0.0010 | 1.002 | 0.954 | 0.037 | 0.799 | 0.799 | 0.000 |
| predicted | all | 53841 | 0.831 | -0.0010 | 0.975 | 0.916 | 0.095 | 0.704 | 0.700 | 0.000 |
| always_strongest | cheapest_above_threshold | 17947 | 0.167 | 0.0018 | 4.798 | 0.948 | 0.043 | 0.794 | 0.582 | 0.007 |
| always_strongest | max_utility | 17947 | 0.257 | 0.1150 | 3.291 | 0.948 | 0.043 | 0.794 | 0.720 | 0.007 |
| always_strongest | max_quality | 17947 | 0.968 | 0.0102 | 0.996 | 0.948 | 0.043 | 0.794 | 0.799 | 0.007 |
| always_strongest | all | 53841 | 0.464 | 0.0423 | 1.978 | 0.948 | 0.043 | 0.794 | 0.700 | 0.007 |
| always_cheapest | cheapest_above_threshold | 17947 | 0.273 | 0.2457 | 0.039 | 0.595 | 0.583 | 0.322 | 0.582 | 0.015 |
| always_cheapest | max_utility | 17947 | 0.080 | 0.3589 | 0.026 | 0.595 | 0.583 | 0.322 | 0.720 | 0.015 |
| always_cheapest | max_quality | 17947 | 0.012 | 0.2541 | 0.008 | 0.595 | 0.583 | 0.322 | 0.799 | 0.015 |
| always_cheapest | all | 53841 | 0.122 | 0.2863 | 0.016 | 0.595 | 0.583 | 0.322 | 0.700 | 0.015 |
