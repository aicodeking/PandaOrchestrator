# Eval: `onnx:artifacts/abl32m_direct` on `gold` (n=285)

Sources: {'swe-rebench': 92, 'swe-smith': 23, 'wildchat': 170}  
Latency (batch 1): p50 16.07 ms, p95 75.338 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.604 / 0.796 / 0.155 |
| difficulty | MAE / Spearman / QWK / ECE | 0.855 / 0.717 / 0.636 / 0.052 |
| skills | mean MAE / mean Spearman / mean ECE | 0.759 / 0.617 / 0.152 |
| flags | F1 macro / AUROC macro / ECE | 0.527 / 0.836 / 0.062 |
| checklist | F1 macro / micro / AUROC | 0.454 / 0.710 / 0.854 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.233 / 0.719 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | 0.080 / 0.004 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 92 | 0.826 | 0.699 | 0.585 | 0.528 | 0.353 |
| swe-smith | 23 | 1.000 | 0.613 | 0.645 | 0.838 | 0.727 |
| wildchat | 170 | 0.429 | 0.973 | 0.630 | 0.244 | 0.330 |

## Routing (cards: cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 14248 | 0.746 | 0.0090 | 0.634 | 0.877 | 0.142 | 0.607 | 0.622 | 0.000 |
| predicted | max_utility | 14248 | 0.881 | 0.0029 | 0.896 | 0.943 | 0.043 | 0.752 | 0.757 | 0.000 |
| predicted | max_quality | 14248 | 0.985 | 0.0022 | 1.007 | 0.974 | 0.012 | 0.853 | 0.853 | 0.000 |
| predicted | all | 42744 | 0.870 | 0.0047 | 0.943 | 0.931 | 0.066 | 0.737 | 0.744 | 0.000 |
| always_strongest | cheapest_above_threshold | 14248 | 0.074 | 0.0310 | 6.393 | 0.974 | 0.012 | 0.853 | 0.622 | 0.000 |
| always_strongest | max_utility | 14248 | 0.124 | 0.1220 | 3.058 | 0.974 | 0.012 | 0.853 | 0.757 | 0.000 |
| always_strongest | max_quality | 14248 | 0.981 | 0.0027 | 1.008 | 0.974 | 0.012 | 0.853 | 0.853 | 0.000 |
| always_strongest | all | 42744 | 0.393 | 0.0519 | 2.033 | 0.974 | 0.012 | 0.853 | 0.744 | 0.000 |
| always_cheapest | cheapest_above_threshold | 14248 | 0.527 | 0.1456 | 0.188 | 0.731 | 0.392 | 0.451 | 0.622 | 0.001 |
| always_cheapest | max_utility | 14248 | 0.183 | 0.2366 | 0.090 | 0.731 | 0.392 | 0.451 | 0.757 | 0.001 |
| always_cheapest | max_quality | 14248 | 0.011 | 0.1173 | 0.029 | 0.731 | 0.392 | 0.451 | 0.853 | 0.001 |
| always_cheapest | all | 42744 | 0.240 | 0.1665 | 0.060 | 0.731 | 0.392 | 0.451 | 0.744 | 0.001 |
