# Eval: `onnx:artifacts/abl32m_pair0` on `gold` (n=285)

Sources: {'swe-rebench': 92, 'swe-smith': 23, 'wildchat': 170}  
Latency (batch 1): p50 12.061 ms, p95 38.106 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.607 / 0.768 / 0.169 |
| difficulty | MAE / Spearman / QWK / ECE | 0.861 / 0.724 / 0.663 / 0.051 |
| skills | mean MAE / mean Spearman / mean ECE | 0.804 / 0.601 / 0.164 |
| flags | F1 macro / AUROC macro / ECE | 0.515 / 0.846 / 0.043 |
| checklist | F1 macro / micro / AUROC | 0.395 / 0.700 / 0.836 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.242 / 0.674 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | 0.102 / 0.004 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 92 | 0.837 | 0.688 | 0.574 | 0.495 | 0.331 |
| swe-smith | 23 | 1.000 | 0.670 | 0.509 | 0.838 | 0.737 |
| wildchat | 170 | 0.429 | 0.981 | 0.640 | 0.208 | 0.267 |

## Routing (cards: cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 14248 | 0.750 | 0.0013 | 0.743 | 0.886 | 0.119 | 0.618 | 0.622 | 0.000 |
| predicted | max_utility | 14248 | 0.875 | 0.0028 | 0.929 | 0.944 | 0.041 | 0.755 | 0.757 | 0.000 |
| predicted | max_quality | 14248 | 0.983 | 0.0023 | 1.007 | 0.974 | 0.012 | 0.853 | 0.853 | 0.000 |
| predicted | all | 42744 | 0.869 | 0.0021 | 0.962 | 0.935 | 0.057 | 0.742 | 0.744 | 0.000 |
| always_strongest | cheapest_above_threshold | 14248 | 0.074 | 0.0310 | 6.393 | 0.974 | 0.012 | 0.853 | 0.622 | 0.000 |
| always_strongest | max_utility | 14248 | 0.124 | 0.1220 | 3.058 | 0.974 | 0.012 | 0.853 | 0.757 | 0.000 |
| always_strongest | max_quality | 14248 | 0.981 | 0.0027 | 1.008 | 0.974 | 0.012 | 0.853 | 0.853 | 0.000 |
| always_strongest | all | 42744 | 0.393 | 0.0519 | 2.033 | 0.974 | 0.012 | 0.853 | 0.744 | 0.000 |
| always_cheapest | cheapest_above_threshold | 14248 | 0.527 | 0.1456 | 0.188 | 0.731 | 0.392 | 0.451 | 0.622 | 0.001 |
| always_cheapest | max_utility | 14248 | 0.183 | 0.2366 | 0.090 | 0.731 | 0.392 | 0.451 | 0.757 | 0.001 |
| always_cheapest | max_quality | 14248 | 0.011 | 0.1173 | 0.029 | 0.731 | 0.392 | 0.451 | 0.853 | 0.001 |
| always_cheapest | all | 42744 | 0.240 | 0.1665 | 0.060 | 0.731 | 0.392 | 0.451 | 0.744 | 0.001 |
