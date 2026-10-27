# Eval: `onnx:artifacts/panda-router-v2` on `test` (n=603)

Sources: {'minimal-pair': 64, 'swe-rebench': 120, 'synthetic': 320, 'wildchat': 99}  
Latency (batch 1): p50 8.894 ms, p95 36.638 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.839 / 0.942 / 0.163 |
| difficulty | MAE / Spearman / QWK / ECE | 0.648 / 0.913 / 0.879 / 0.060 |
| skills | mean MAE / mean Spearman / mean ECE | 0.800 / 0.830 / 0.098 |
| flags | F1 macro / AUROC macro / ECE | 0.832 / 0.931 / 0.030 |
| checklist | F1 macro / micro / AUROC | 0.738 / 0.825 / 0.916 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.128 / 0.924 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 64 | 0.891 | 0.476 | 0.927 | 0.787 | 0.731 |
| swe-rebench | 120 | 0.925 | 0.698 | 0.597 | 0.678 | 0.421 |
| synthetic | 320 | 0.787 | 0.648 | 0.870 | 0.871 | 0.745 |
| wildchat | 99 | 0.869 | 0.699 | 0.769 | 0.362 | 0.398 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 30097 | 0.752 | 0.0081 | 0.993 | 0.742 | 0.407 | 0.540 | 0.553 | 0.000 |
| predicted | max_utility | 30097 | 0.879 | -0.0002 | 0.892 | 0.773 | 0.359 | 0.608 | 0.619 | 0.000 |
| predicted | max_quality | 30097 | 0.990 | 0.0001 | 1.004 | 0.810 | 0.287 | 0.679 | 0.679 | 0.000 |
| predicted | all | 90291 | 0.874 | 0.0027 | 0.971 | 0.775 | 0.351 | 0.609 | 0.617 | 0.000 |
| always_strongest | cheapest_above_threshold | 30097 | 0.458 | 0.0163 | 1.412 | 0.803 | 0.292 | 0.674 | 0.553 | 0.012 |
| always_strongest | max_utility | 30097 | 0.450 | 0.0816 | 1.611 | 0.803 | 0.292 | 0.674 | 0.619 | 0.012 |
| always_strongest | max_quality | 30097 | 0.965 | 0.0143 | 1.006 | 0.803 | 0.292 | 0.674 | 0.679 | 0.012 |
| always_strongest | all | 90291 | 0.624 | 0.0374 | 1.291 | 0.803 | 0.292 | 0.674 | 0.617 | 0.012 |
| always_cheapest | cheapest_above_threshold | 30097 | 0.136 | 0.3452 | 0.012 | 0.349 | 0.805 | 0.189 | 0.553 | 0.102 |
| always_cheapest | max_utility | 30097 | 0.049 | 0.4105 | 0.014 | 0.349 | 0.805 | 0.189 | 0.619 | 0.102 |
| always_cheapest | max_quality | 30097 | 0.013 | 0.3432 | 0.009 | 0.349 | 0.805 | 0.189 | 0.679 | 0.102 |
| always_cheapest | all | 90291 | 0.066 | 0.3663 | 0.011 | 0.349 | 0.805 | 0.189 | 0.617 | 0.102 |
