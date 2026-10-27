# Eval: `onnx:artifacts/panda-router-v1` on `test` (n=603)

Sources: {'minimal-pair': 64, 'swe-rebench': 120, 'synthetic': 320, 'wildchat': 99}  
Latency (batch 1): p50 5.824 ms, p95 23.15 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.786 / 0.876 / 0.094 |
| difficulty | MAE / Spearman / QWK / ECE | 0.698 / 0.885 / 0.852 / 0.034 |
| skills | mean MAE / mean Spearman / mean ECE | 0.977 / 0.788 / 0.096 |
| flags | F1 macro / AUROC macro / ECE | 0.801 / 0.923 / 0.037 |
| checklist | F1 macro / micro / AUROC | 0.629 / 0.791 / 0.887 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.161 / 0.864 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 64 | 0.922 | 0.408 | 0.937 | 0.782 | 0.654 |
| swe-rebench | 120 | 0.942 | 0.607 | 0.701 | 0.640 | 0.390 |
| synthetic | 320 | 0.675 | 0.801 | 0.753 | 0.830 | 0.612 |
| wildchat | 99 | 0.869 | 0.664 | 0.793 | 0.366 | 0.404 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 30097 | 0.732 | -0.0044 | 1.017 | 0.756 | 0.366 | 0.560 | 0.553 | 0.000 |
| predicted | max_utility | 30097 | 0.864 | -0.0018 | 0.867 | 0.772 | 0.357 | 0.609 | 0.619 | 0.000 |
| predicted | max_quality | 30097 | 0.988 | 0.0004 | 1.006 | 0.810 | 0.287 | 0.679 | 0.679 | 0.000 |
| predicted | all | 90291 | 0.861 | -0.0019 | 0.972 | 0.779 | 0.337 | 0.616 | 0.617 | 0.000 |
| always_strongest | cheapest_above_threshold | 30097 | 0.458 | 0.0163 | 1.412 | 0.803 | 0.292 | 0.674 | 0.553 | 0.012 |
| always_strongest | max_utility | 30097 | 0.450 | 0.0816 | 1.611 | 0.803 | 0.292 | 0.674 | 0.619 | 0.012 |
| always_strongest | max_quality | 30097 | 0.965 | 0.0143 | 1.006 | 0.803 | 0.292 | 0.674 | 0.679 | 0.012 |
| always_strongest | all | 90291 | 0.624 | 0.0374 | 1.291 | 0.803 | 0.292 | 0.674 | 0.617 | 0.012 |
| always_cheapest | cheapest_above_threshold | 30097 | 0.136 | 0.3452 | 0.012 | 0.349 | 0.805 | 0.189 | 0.553 | 0.102 |
| always_cheapest | max_utility | 30097 | 0.049 | 0.4105 | 0.014 | 0.349 | 0.805 | 0.189 | 0.619 | 0.102 |
| always_cheapest | max_quality | 30097 | 0.013 | 0.3432 | 0.009 | 0.349 | 0.805 | 0.189 | 0.679 | 0.102 |
| always_cheapest | all | 90291 | 0.066 | 0.3663 | 0.011 | 0.349 | 0.805 | 0.189 | 0.617 | 0.102 |
