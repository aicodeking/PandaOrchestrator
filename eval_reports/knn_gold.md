# Eval: `knn` on `gold` (n=285)

Sources: {'swe-rebench': 92, 'swe-smith': 23, 'wildchat': 170}  
Latency (batch 1): p50 37.0 ms, p95 98.18 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.579 / 0.719 / 0.096 |
| difficulty | MAE / Spearman / QWK / ECE | 1.099 / 0.487 / 0.463 / 0.050 |
| skills | mean MAE / mean Spearman / mean ECE | 0.940 / 0.467 / 0.160 |
| flags | F1 macro / AUROC macro / ECE | 0.362 / 0.710 / 0.078 |
| checklist | F1 macro / micro / AUROC | 0.392 / 0.658 / 0.753 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.290 / 0.810 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | 0.033 / 0.004 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 92 | 0.815 | 0.868 | 0.187 | 0.323 | 0.306 |
| swe-smith | 23 | 1.000 | 0.750 | 0.503 | 0.341 | 0.501 |
| wildchat | 170 | 0.394 | 1.271 | 0.455 | 0.264 | 0.321 |

## Routing (cards: cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 14248 | 0.677 | -0.0098 | 0.721 | 0.892 | 0.123 | 0.636 | 0.622 | 0.000 |
| predicted | max_utility | 14248 | 0.838 | 0.0043 | 0.933 | 0.944 | 0.044 | 0.759 | 0.757 | 0.000 |
| predicted | max_quality | 14248 | 0.984 | 0.0020 | 1.007 | 0.974 | 0.012 | 0.853 | 0.853 | 0.000 |
| predicted | all | 42744 | 0.833 | -0.0011 | 0.960 | 0.937 | 0.060 | 0.749 | 0.744 | 0.000 |
| always_strongest | cheapest_above_threshold | 14248 | 0.074 | 0.0310 | 6.393 | 0.974 | 0.012 | 0.853 | 0.622 | 0.000 |
| always_strongest | max_utility | 14248 | 0.124 | 0.1220 | 3.058 | 0.974 | 0.012 | 0.853 | 0.757 | 0.000 |
| always_strongest | max_quality | 14248 | 0.981 | 0.0027 | 1.008 | 0.974 | 0.012 | 0.853 | 0.853 | 0.000 |
| always_strongest | all | 42744 | 0.393 | 0.0519 | 2.033 | 0.974 | 0.012 | 0.853 | 0.744 | 0.000 |
| always_cheapest | cheapest_above_threshold | 14248 | 0.527 | 0.1456 | 0.188 | 0.731 | 0.392 | 0.451 | 0.622 | 0.001 |
| always_cheapest | max_utility | 14248 | 0.183 | 0.2366 | 0.090 | 0.731 | 0.392 | 0.451 | 0.757 | 0.001 |
| always_cheapest | max_quality | 14248 | 0.011 | 0.1173 | 0.029 | 0.731 | 0.392 | 0.451 | 0.853 | 0.001 |
| always_cheapest | all | 42744 | 0.240 | 0.1665 | 0.060 | 0.731 | 0.392 | 0.451 | 0.744 | 0.001 |
