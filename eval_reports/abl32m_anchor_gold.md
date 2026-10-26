# Eval: `onnx:artifacts/abl32m_anchor` on `gold` (n=285)

Sources: {'swe-rebench': 92, 'swe-smith': 23, 'wildchat': 170}  
Latency (batch 1): p50 24.8 ms, p95 196.416 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.604 / 0.768 / 0.142 |
| difficulty | MAE / Spearman / QWK / ECE | 0.878 / 0.718 / 0.687 / 0.068 |
| skills | mean MAE / mean Spearman / mean ECE | 0.803 / 0.604 / 0.163 |
| flags | F1 macro / AUROC macro / ECE | 0.517 / 0.877 / 0.050 |
| checklist | F1 macro / micro / AUROC | 0.396 / 0.709 / 0.839 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.250 / 0.621 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | 0.134 / 0.004 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 92 | 0.804 | 0.731 | 0.402 | 0.515 | 0.336 |
| swe-smith | 23 | 1.000 | 0.637 | 0.637 | 0.838 | 0.679 |
| wildchat | 170 | 0.441 | 0.991 | 0.642 | 0.236 | 0.272 |

## Routing (cards: cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 14248 | 0.711 | -0.0047 | 0.869 | 0.892 | 0.111 | 0.629 | 0.622 | 0.000 |
| predicted | max_utility | 14248 | 0.868 | 0.0030 | 0.985 | 0.946 | 0.039 | 0.759 | 0.757 | 0.000 |
| predicted | max_quality | 14248 | 0.983 | 0.0023 | 1.007 | 0.974 | 0.012 | 0.853 | 0.853 | 0.000 |
| predicted | all | 42744 | 0.854 | 0.0002 | 0.988 | 0.937 | 0.054 | 0.747 | 0.744 | 0.000 |
| always_strongest | cheapest_above_threshold | 14248 | 0.074 | 0.0310 | 6.393 | 0.974 | 0.012 | 0.853 | 0.622 | 0.000 |
| always_strongest | max_utility | 14248 | 0.124 | 0.1220 | 3.058 | 0.974 | 0.012 | 0.853 | 0.757 | 0.000 |
| always_strongest | max_quality | 14248 | 0.981 | 0.0027 | 1.008 | 0.974 | 0.012 | 0.853 | 0.853 | 0.000 |
| always_strongest | all | 42744 | 0.393 | 0.0519 | 2.033 | 0.974 | 0.012 | 0.853 | 0.744 | 0.000 |
| always_cheapest | cheapest_above_threshold | 14248 | 0.527 | 0.1456 | 0.188 | 0.731 | 0.392 | 0.451 | 0.622 | 0.001 |
| always_cheapest | max_utility | 14248 | 0.183 | 0.2366 | 0.090 | 0.731 | 0.392 | 0.451 | 0.757 | 0.001 |
| always_cheapest | max_quality | 14248 | 0.011 | 0.1173 | 0.029 | 0.731 | 0.392 | 0.451 | 0.853 | 0.001 |
| always_cheapest | all | 42744 | 0.240 | 0.1665 | 0.060 | 0.731 | 0.392 | 0.451 | 0.744 | 0.001 |
