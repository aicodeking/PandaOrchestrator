# Eval: `onnx:artifacts/s68m_soup` on `gold` (n=285)

Sources: {'swe-rebench': 92, 'swe-smith': 23, 'wildchat': 170}  
Latency (batch 1): p50 49.756 ms, p95 227.377 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.628 / 0.789 / 0.140 |
| difficulty | MAE / Spearman / QWK / ECE | 0.866 / 0.719 / 0.643 / 0.029 |
| skills | mean MAE / mean Spearman / mean ECE | 0.792 / 0.594 / 0.152 |
| flags | F1 macro / AUROC macro / ECE | 0.509 / 0.859 / 0.050 |
| checklist | F1 macro / micro / AUROC | 0.407 / 0.713 / 0.837 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.246 / 0.628 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | 0.099 / 0.004 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 92 | 0.859 | 0.710 | 0.536 | 0.504 | 0.329 |
| swe-smith | 23 | 1.000 | 0.608 | 0.491 | 0.824 | 0.699 |
| wildchat | 170 | 0.453 | 0.985 | 0.649 | 0.196 | 0.278 |

## Routing (cards: cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 14248 | 0.754 | -0.0008 | 0.648 | 0.885 | 0.124 | 0.616 | 0.622 | 0.000 |
| predicted | max_utility | 14248 | 0.878 | 0.0027 | 0.916 | 0.944 | 0.043 | 0.754 | 0.757 | 0.000 |
| predicted | max_quality | 14248 | 0.983 | 0.0023 | 1.007 | 0.974 | 0.012 | 0.853 | 0.853 | 0.000 |
| predicted | all | 42744 | 0.872 | 0.0014 | 0.949 | 0.934 | 0.060 | 0.741 | 0.744 | 0.000 |
| always_strongest | cheapest_above_threshold | 14248 | 0.074 | 0.0310 | 6.393 | 0.974 | 0.012 | 0.853 | 0.622 | 0.000 |
| always_strongest | max_utility | 14248 | 0.124 | 0.1220 | 3.058 | 0.974 | 0.012 | 0.853 | 0.757 | 0.000 |
| always_strongest | max_quality | 14248 | 0.981 | 0.0027 | 1.008 | 0.974 | 0.012 | 0.853 | 0.853 | 0.000 |
| always_strongest | all | 42744 | 0.393 | 0.0519 | 2.033 | 0.974 | 0.012 | 0.853 | 0.744 | 0.000 |
| always_cheapest | cheapest_above_threshold | 14248 | 0.527 | 0.1456 | 0.188 | 0.731 | 0.392 | 0.451 | 0.622 | 0.001 |
| always_cheapest | max_utility | 14248 | 0.183 | 0.2366 | 0.090 | 0.731 | 0.392 | 0.451 | 0.757 | 0.001 |
| always_cheapest | max_quality | 14248 | 0.011 | 0.1173 | 0.029 | 0.731 | 0.392 | 0.451 | 0.853 | 0.001 |
| always_cheapest | all | 42744 | 0.240 | 0.1665 | 0.060 | 0.731 | 0.392 | 0.451 | 0.744 | 0.001 |
