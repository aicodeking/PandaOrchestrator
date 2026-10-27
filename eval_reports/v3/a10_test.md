# Eval: `onnx:artifacts/v3_32_a10_onnx` on `test` (n=603)

Sources: {'minimal-pair': 64, 'swe-rebench': 120, 'synthetic': 320, 'wildchat': 99}  
Latency (batch 1): p50 5.376 ms, p95 20.601 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.748 / 0.907 / 0.072 |
| difficulty | MAE / Spearman / QWK / ECE | 0.884 / 0.845 / 0.770 / 0.029 |
| skills | mean MAE / mean Spearman / mean ECE | 0.883 / 0.798 / 0.075 |
| flags | F1 macro / AUROC macro / ECE | 0.792 / 0.915 / 0.031 |
| checklist | F1 macro / micro / AUROC | 0.698 / 0.802 / 0.902 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.176 / 0.794 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 64 | 0.703 | 0.881 | 0.762 | 0.748 | 0.683 |
| swe-rebench | 120 | 0.908 | 0.805 | 0.484 | 0.594 | 0.389 |
| synthetic | 320 | 0.669 | 0.777 | 0.808 | 0.836 | 0.699 |
| wildchat | 99 | 0.838 | 1.327 | 0.432 | 0.249 | 0.345 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 30097 | 0.665 | -0.0055 | 0.973 | 0.752 | 0.399 | 0.563 | 0.553 | 0.000 |
| predicted | max_utility | 30097 | 0.849 | -0.0002 | 0.841 | 0.770 | 0.363 | 0.609 | 0.619 | 0.000 |
| predicted | max_quality | 30097 | 0.990 | 0.0003 | 1.006 | 0.810 | 0.287 | 0.679 | 0.679 | 0.000 |
| predicted | all | 90291 | 0.835 | -0.0018 | 0.952 | 0.777 | 0.349 | 0.617 | 0.617 | 0.000 |
| always_strongest | cheapest_above_threshold | 30097 | 0.458 | 0.0163 | 1.412 | 0.803 | 0.292 | 0.674 | 0.553 | 0.012 |
| always_strongest | max_utility | 30097 | 0.450 | 0.0816 | 1.611 | 0.803 | 0.292 | 0.674 | 0.619 | 0.012 |
| always_strongest | max_quality | 30097 | 0.965 | 0.0143 | 1.006 | 0.803 | 0.292 | 0.674 | 0.679 | 0.012 |
| always_strongest | all | 90291 | 0.624 | 0.0374 | 1.291 | 0.803 | 0.292 | 0.674 | 0.617 | 0.012 |
| always_cheapest | cheapest_above_threshold | 30097 | 0.136 | 0.3452 | 0.012 | 0.349 | 0.805 | 0.189 | 0.553 | 0.102 |
| always_cheapest | max_utility | 30097 | 0.049 | 0.4105 | 0.014 | 0.349 | 0.805 | 0.189 | 0.619 | 0.102 |
| always_cheapest | max_quality | 30097 | 0.013 | 0.3432 | 0.009 | 0.349 | 0.805 | 0.189 | 0.679 | 0.102 |
| always_cheapest | all | 90291 | 0.066 | 0.3663 | 0.011 | 0.349 | 0.805 | 0.189 | 0.617 | 0.102 |
