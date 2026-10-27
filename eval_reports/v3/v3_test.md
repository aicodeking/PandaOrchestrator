# Eval: `onnx:artifacts/panda-router-v3` on `test` (n=603)

Sources: {'minimal-pair': 64, 'swe-rebench': 120, 'synthetic': 320, 'wildchat': 99}  
Latency (batch 1): p50 4.73 ms, p95 17.71 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.789 / 0.939 / 0.076 |
| difficulty | MAE / Spearman / QWK / ECE | 0.728 / 0.885 / 0.844 / 0.024 |
| skills | mean MAE / mean Spearman / mean ECE | 0.800 / 0.822 / 0.093 |
| flags | F1 macro / AUROC macro / ECE | 0.841 / 0.923 / 0.028 |
| checklist | F1 macro / micro / AUROC | 0.753 / 0.824 / 0.914 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.170 / 0.813 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 64 | 0.766 | 0.728 | 0.850 | 0.761 | 0.699 |
| swe-rebench | 120 | 0.892 | 0.740 | 0.552 | 0.680 | 0.451 |
| synthetic | 320 | 0.750 | 0.651 | 0.844 | 0.900 | 0.767 |
| wildchat | 99 | 0.808 | 0.964 | 0.520 | 0.239 | 0.384 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 30097 | 0.724 | 0.0032 | 1.012 | 0.749 | 0.393 | 0.552 | 0.553 | 0.000 |
| predicted | max_utility | 30097 | 0.875 | 0.0011 | 0.950 | 0.776 | 0.354 | 0.613 | 0.619 | 0.000 |
| predicted | max_quality | 30097 | 0.990 | 0.0002 | 1.004 | 0.810 | 0.287 | 0.679 | 0.679 | 0.000 |
| predicted | all | 90291 | 0.863 | 0.0015 | 0.992 | 0.778 | 0.345 | 0.615 | 0.617 | 0.000 |
| always_strongest | cheapest_above_threshold | 30097 | 0.458 | 0.0163 | 1.412 | 0.803 | 0.292 | 0.674 | 0.553 | 0.012 |
| always_strongest | max_utility | 30097 | 0.450 | 0.0816 | 1.611 | 0.803 | 0.292 | 0.674 | 0.619 | 0.012 |
| always_strongest | max_quality | 30097 | 0.965 | 0.0143 | 1.006 | 0.803 | 0.292 | 0.674 | 0.679 | 0.012 |
| always_strongest | all | 90291 | 0.624 | 0.0374 | 1.291 | 0.803 | 0.292 | 0.674 | 0.617 | 0.012 |
| always_cheapest | cheapest_above_threshold | 30097 | 0.136 | 0.3452 | 0.012 | 0.349 | 0.805 | 0.189 | 0.553 | 0.102 |
| always_cheapest | max_utility | 30097 | 0.049 | 0.4105 | 0.014 | 0.349 | 0.805 | 0.189 | 0.619 | 0.102 |
| always_cheapest | max_quality | 30097 | 0.013 | 0.3432 | 0.009 | 0.349 | 0.805 | 0.189 | 0.679 | 0.102 |
| always_cheapest | all | 90291 | 0.066 | 0.3663 | 0.011 | 0.349 | 0.805 | 0.189 | 0.617 | 0.102 |
