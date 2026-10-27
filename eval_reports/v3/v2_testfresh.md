# Eval: `onnx:artifacts/panda-router-v2` on `test` (n=310)

Sources: {'minimal-pair': 15, 'swe-rebench': 72, 'synthetic': 168, 'wildchat': 55}  
Latency (batch 1): p50 6.574 ms, p95 25.17 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.790 / 0.903 / 0.125 |
| difficulty | MAE / Spearman / QWK / ECE | 0.780 / 0.874 / 0.817 / 0.023 |
| skills | mean MAE / mean Spearman / mean ECE | 0.881 / 0.796 / 0.088 |
| flags | F1 macro / AUROC macro / ECE | 0.807 / 0.913 / 0.047 |
| checklist | F1 macro / micro / AUROC | 0.698 / 0.799 / 0.897 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.162 / 0.858 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 15 | 0.800 | 0.620 | 0.915 | 0.761 | 0.634 |
| swe-rebench | 72 | 0.917 | 0.774 | 0.525 | 0.626 | 0.406 |
| synthetic | 168 | 0.732 | 0.750 | 0.828 | 0.857 | 0.717 |
| wildchat | 55 | 0.800 | 0.927 | 0.582 | 0.217 | 0.313 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 15461 | 0.695 | 0.0113 | 0.974 | 0.739 | 0.432 | 0.536 | 0.558 | 0.000 |
| predicted | max_utility | 15461 | 0.854 | -0.0004 | 0.819 | 0.777 | 0.359 | 0.611 | 0.625 | 0.000 |
| predicted | max_quality | 15461 | 0.991 | 0.0002 | 1.007 | 0.819 | 0.276 | 0.687 | 0.687 | 0.000 |
| predicted | all | 46383 | 0.846 | 0.0037 | 0.945 | 0.778 | 0.356 | 0.611 | 0.623 | 0.000 |
| always_strongest | cheapest_above_threshold | 15461 | 0.455 | 0.0138 | 1.364 | 0.812 | 0.281 | 0.682 | 0.558 | 0.011 |
| always_strongest | max_utility | 15461 | 0.446 | 0.0807 | 1.528 | 0.812 | 0.281 | 0.682 | 0.625 | 0.011 |
| always_strongest | max_quality | 15461 | 0.966 | 0.0130 | 1.006 | 0.812 | 0.281 | 0.682 | 0.687 | 0.011 |
| always_strongest | all | 46383 | 0.623 | 0.0358 | 1.260 | 0.812 | 0.281 | 0.682 | 0.623 | 0.011 |
| always_cheapest | cheapest_above_threshold | 15461 | 0.142 | 0.3513 | 0.012 | 0.356 | 0.801 | 0.193 | 0.558 | 0.102 |
| always_cheapest | max_utility | 15461 | 0.051 | 0.4182 | 0.014 | 0.356 | 0.801 | 0.193 | 0.625 | 0.102 |
| always_cheapest | max_quality | 15461 | 0.013 | 0.3504 | 0.009 | 0.356 | 0.801 | 0.193 | 0.687 | 0.102 |
| always_cheapest | all | 46383 | 0.068 | 0.3733 | 0.011 | 0.356 | 0.801 | 0.193 | 0.623 | 0.102 |
