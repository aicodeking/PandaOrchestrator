# Eval: `onnx:artifacts/v3_32_a10_onnx` on `test` (n=310)

Sources: {'minimal-pair': 15, 'swe-rebench': 72, 'synthetic': 168, 'wildchat': 55}  
Latency (batch 1): p50 8.547 ms, p95 73.281 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.768 / 0.919 / 0.089 |
| difficulty | MAE / Spearman / QWK / ECE | 0.879 / 0.832 / 0.753 / 0.037 |
| skills | mean MAE / mean Spearman / mean ECE | 0.885 / 0.789 / 0.092 |
| flags | F1 macro / AUROC macro / ECE | 0.783 / 0.916 / 0.041 |
| checklist | F1 macro / micro / AUROC | 0.688 / 0.794 / 0.901 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.173 / 0.813 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 15 | 0.600 | 0.699 | 0.895 | 0.746 | 0.602 |
| swe-rebench | 72 | 0.944 | 0.775 | 0.559 | 0.604 | 0.409 |
| synthetic | 168 | 0.696 | 0.805 | 0.789 | 0.825 | 0.692 |
| wildchat | 55 | 0.800 | 1.295 | 0.376 | 0.260 | 0.372 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 15461 | 0.651 | -0.0029 | 0.963 | 0.753 | 0.408 | 0.562 | 0.558 | 0.000 |
| predicted | max_utility | 15461 | 0.849 | -0.0008 | 0.786 | 0.776 | 0.359 | 0.611 | 0.625 | 0.000 |
| predicted | max_quality | 15461 | 0.991 | 0.0003 | 1.007 | 0.819 | 0.276 | 0.687 | 0.687 | 0.000 |
| predicted | all | 46383 | 0.830 | -0.0012 | 0.933 | 0.783 | 0.348 | 0.620 | 0.623 | 0.000 |
| always_strongest | cheapest_above_threshold | 15461 | 0.455 | 0.0138 | 1.364 | 0.812 | 0.281 | 0.682 | 0.558 | 0.011 |
| always_strongest | max_utility | 15461 | 0.446 | 0.0807 | 1.528 | 0.812 | 0.281 | 0.682 | 0.625 | 0.011 |
| always_strongest | max_quality | 15461 | 0.966 | 0.0130 | 1.006 | 0.812 | 0.281 | 0.682 | 0.687 | 0.011 |
| always_strongest | all | 46383 | 0.623 | 0.0358 | 1.260 | 0.812 | 0.281 | 0.682 | 0.623 | 0.011 |
| always_cheapest | cheapest_above_threshold | 15461 | 0.142 | 0.3513 | 0.012 | 0.356 | 0.801 | 0.193 | 0.558 | 0.102 |
| always_cheapest | max_utility | 15461 | 0.051 | 0.4182 | 0.014 | 0.356 | 0.801 | 0.193 | 0.625 | 0.102 |
| always_cheapest | max_quality | 15461 | 0.013 | 0.3504 | 0.009 | 0.356 | 0.801 | 0.193 | 0.687 | 0.102 |
| always_cheapest | all | 46383 | 0.068 | 0.3733 | 0.011 | 0.356 | 0.801 | 0.193 | 0.623 | 0.102 |
