# Eval: `onnx:artifacts/s32m_soup` on `gold` (n=285)

Sources: {'swe-rebench': 92, 'swe-smith': 23, 'wildchat': 170}  
Latency (batch 1): p50 7.264 ms, p95 21.868 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.614 / 0.772 / 0.159 |
| difficulty | MAE / Spearman / QWK / ECE | 0.842 / 0.718 / 0.660 / 0.047 |
| skills | mean MAE / mean Spearman / mean ECE | 0.776 / 0.601 / 0.147 |
| flags | F1 macro / AUROC macro / ECE | 0.510 / 0.847 / 0.041 |
| checklist | F1 macro / micro / AUROC | 0.407 / 0.705 / 0.830 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.220 / 0.800 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | 0.038 / 0.004 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 92 | 0.837 | 0.663 | 0.580 | 0.495 | 0.337 |
| swe-smith | 23 | 1.000 | 0.625 | 0.615 | 0.803 | 0.681 |
| wildchat | 170 | 0.441 | 0.968 | 0.624 | 0.183 | 0.280 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 14248 | 0.763 | 0.0089 | 0.668 | 0.878 | 0.135 | 0.606 | 0.622 | 0.000 |
| predicted | max_utility | 14248 | 0.882 | 0.0025 | 0.925 | 0.944 | 0.041 | 0.753 | 0.757 | 0.000 |
| predicted | max_quality | 14248 | 0.983 | 0.0023 | 1.007 | 0.974 | 0.012 | 0.853 | 0.853 | 0.000 |
| predicted | all | 42744 | 0.876 | 0.0046 | 0.953 | 0.932 | 0.063 | 0.738 | 0.744 | 0.000 |
| always_strongest | cheapest_above_threshold | 14248 | 0.074 | 0.0310 | 6.393 | 0.974 | 0.012 | 0.853 | 0.622 | 0.000 |
| always_strongest | max_utility | 14248 | 0.124 | 0.1220 | 3.058 | 0.974 | 0.012 | 0.853 | 0.757 | 0.000 |
| always_strongest | max_quality | 14248 | 0.981 | 0.0027 | 1.008 | 0.974 | 0.012 | 0.853 | 0.853 | 0.000 |
| always_strongest | all | 42744 | 0.393 | 0.0519 | 2.033 | 0.974 | 0.012 | 0.853 | 0.744 | 0.000 |
| always_cheapest | cheapest_above_threshold | 14248 | 0.527 | 0.1456 | 0.188 | 0.731 | 0.392 | 0.451 | 0.622 | 0.001 |
| always_cheapest | max_utility | 14248 | 0.183 | 0.2366 | 0.090 | 0.731 | 0.392 | 0.451 | 0.757 | 0.001 |
| always_cheapest | max_quality | 14248 | 0.011 | 0.1173 | 0.029 | 0.731 | 0.392 | 0.451 | 0.853 | 0.001 |
| always_cheapest | all | 42744 | 0.240 | 0.1665 | 0.060 | 0.731 | 0.392 | 0.451 | 0.744 | 0.001 |
