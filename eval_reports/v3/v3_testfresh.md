# Eval: `onnx:artifacts/panda-router-v3` on `test` (n=310)

Sources: {'minimal-pair': 15, 'swe-rebench': 72, 'synthetic': 168, 'wildchat': 55}  
Latency (batch 1): p50 5.238 ms, p95 18.227 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.839 / 0.948 / 0.098 |
| difficulty | MAE / Spearman / QWK / ECE | 0.718 / 0.876 / 0.833 / 0.021 |
| skills | mean MAE / mean Spearman / mean ECE | 0.795 / 0.812 / 0.103 |
| flags | F1 macro / AUROC macro / ECE | 0.842 / 0.923 / 0.042 |
| checklist | F1 macro / micro / AUROC | 0.749 / 0.823 / 0.910 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.161 / 0.829 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 15 | 0.800 | 0.662 | 0.917 | 0.743 | 0.615 |
| swe-rebench | 72 | 0.931 | 0.691 | 0.629 | 0.659 | 0.470 |
| synthetic | 168 | 0.809 | 0.654 | 0.840 | 0.914 | 0.767 |
| wildchat | 55 | 0.818 | 0.962 | 0.577 | 0.256 | 0.382 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 15461 | 0.716 | 0.0063 | 1.009 | 0.750 | 0.402 | 0.549 | 0.558 | 0.000 |
| predicted | max_utility | 15461 | 0.878 | 0.0005 | 0.905 | 0.782 | 0.352 | 0.617 | 0.625 | 0.000 |
| predicted | max_quality | 15461 | 0.992 | 0.0003 | 1.007 | 0.819 | 0.276 | 0.687 | 0.687 | 0.000 |
| predicted | all | 46383 | 0.862 | 0.0024 | 0.980 | 0.784 | 0.343 | 0.618 | 0.623 | 0.000 |
| always_strongest | cheapest_above_threshold | 15461 | 0.455 | 0.0138 | 1.364 | 0.812 | 0.281 | 0.682 | 0.558 | 0.011 |
| always_strongest | max_utility | 15461 | 0.446 | 0.0807 | 1.528 | 0.812 | 0.281 | 0.682 | 0.625 | 0.011 |
| always_strongest | max_quality | 15461 | 0.966 | 0.0130 | 1.006 | 0.812 | 0.281 | 0.682 | 0.687 | 0.011 |
| always_strongest | all | 46383 | 0.623 | 0.0358 | 1.260 | 0.812 | 0.281 | 0.682 | 0.623 | 0.011 |
| always_cheapest | cheapest_above_threshold | 15461 | 0.142 | 0.3513 | 0.012 | 0.356 | 0.801 | 0.193 | 0.558 | 0.102 |
| always_cheapest | max_utility | 15461 | 0.051 | 0.4182 | 0.014 | 0.356 | 0.801 | 0.193 | 0.625 | 0.102 |
| always_cheapest | max_quality | 15461 | 0.013 | 0.3504 | 0.009 | 0.356 | 0.801 | 0.193 | 0.687 | 0.102 |
| always_cheapest | all | 46383 | 0.068 | 0.3733 | 0.011 | 0.356 | 0.801 | 0.193 | 0.623 | 0.102 |
