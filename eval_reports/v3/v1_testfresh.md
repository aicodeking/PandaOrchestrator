# Eval: `onnx:artifacts/panda-router-v1` on `test` (n=310)

Sources: {'minimal-pair': 15, 'swe-rebench': 72, 'synthetic': 168, 'wildchat': 55}  
Latency (batch 1): p50 5.284 ms, p95 20.67 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.781 / 0.861 / 0.079 |
| difficulty | MAE / Spearman / QWK / ECE | 0.723 / 0.876 / 0.829 / 0.022 |
| skills | mean MAE / mean Spearman / mean ECE | 0.980 / 0.775 / 0.104 |
| flags | F1 macro / AUROC macro / ECE | 0.780 / 0.914 / 0.046 |
| checklist | F1 macro / micro / AUROC | 0.623 / 0.784 / 0.879 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.173 / 0.839 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 15 | 0.933 | 0.371 | 0.960 | 0.779 | 0.642 |
| swe-rebench | 72 | 0.917 | 0.619 | 0.624 | 0.615 | 0.408 |
| synthetic | 168 | 0.696 | 0.741 | 0.788 | 0.814 | 0.615 |
| wildchat | 55 | 0.818 | 0.901 | 0.639 | 0.238 | 0.345 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 15461 | 0.711 | -0.0024 | 1.020 | 0.759 | 0.376 | 0.561 | 0.558 | 0.000 |
| predicted | max_utility | 15461 | 0.858 | -0.0009 | 0.826 | 0.779 | 0.351 | 0.615 | 0.625 | 0.000 |
| predicted | max_quality | 15461 | 0.988 | 0.0005 | 1.008 | 0.819 | 0.276 | 0.687 | 0.687 | 0.000 |
| predicted | all | 46383 | 0.853 | -0.0010 | 0.961 | 0.786 | 0.335 | 0.621 | 0.623 | 0.000 |
| always_strongest | cheapest_above_threshold | 15461 | 0.455 | 0.0138 | 1.364 | 0.812 | 0.281 | 0.682 | 0.558 | 0.011 |
| always_strongest | max_utility | 15461 | 0.446 | 0.0807 | 1.528 | 0.812 | 0.281 | 0.682 | 0.625 | 0.011 |
| always_strongest | max_quality | 15461 | 0.966 | 0.0130 | 1.006 | 0.812 | 0.281 | 0.682 | 0.687 | 0.011 |
| always_strongest | all | 46383 | 0.623 | 0.0358 | 1.260 | 0.812 | 0.281 | 0.682 | 0.623 | 0.011 |
| always_cheapest | cheapest_above_threshold | 15461 | 0.142 | 0.3513 | 0.012 | 0.356 | 0.801 | 0.193 | 0.558 | 0.102 |
| always_cheapest | max_utility | 15461 | 0.051 | 0.4182 | 0.014 | 0.356 | 0.801 | 0.193 | 0.625 | 0.102 |
| always_cheapest | max_quality | 15461 | 0.013 | 0.3504 | 0.009 | 0.356 | 0.801 | 0.193 | 0.687 | 0.102 |
| always_cheapest | all | 46383 | 0.068 | 0.3733 | 0.011 | 0.356 | 0.801 | 0.193 | 0.623 | 0.102 |
