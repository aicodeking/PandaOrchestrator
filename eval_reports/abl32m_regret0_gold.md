# Eval: `onnx:artifacts/abl32m_regret0` on `gold` (n=285)

Sources: {'swe-rebench': 92, 'swe-smith': 23, 'wildchat': 170}  
Latency (batch 1): p50 12.81 ms, p95 52.241 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.628 / 0.782 / 0.156 |
| difficulty | MAE / Spearman / QWK / ECE | 0.850 / 0.735 / 0.662 / 0.025 |
| skills | mean MAE / mean Spearman / mean ECE | 0.796 / 0.598 / 0.154 |
| flags | F1 macro / AUROC macro / ECE | 0.503 / 0.843 / 0.045 |
| checklist | F1 macro / micro / AUROC | 0.395 / 0.698 / 0.826 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.222 / 0.740 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | 0.124 / 0.004 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 92 | 0.815 | 0.733 | 0.552 | 0.487 | 0.328 |
| swe-smith | 23 | 1.000 | 0.665 | 0.544 | 0.799 | 0.608 |
| wildchat | 170 | 0.476 | 0.938 | 0.660 | 0.203 | 0.277 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 14248 | 0.761 | 0.0024 | 0.584 | 0.881 | 0.130 | 0.612 | 0.622 | 0.000 |
| predicted | max_utility | 14248 | 0.878 | 0.0026 | 0.907 | 0.943 | 0.043 | 0.753 | 0.757 | 0.000 |
| predicted | max_quality | 14248 | 0.983 | 0.0023 | 1.007 | 0.974 | 0.012 | 0.853 | 0.853 | 0.000 |
| predicted | all | 42744 | 0.874 | 0.0024 | 0.940 | 0.933 | 0.062 | 0.739 | 0.744 | 0.000 |
| always_strongest | cheapest_above_threshold | 14248 | 0.074 | 0.0310 | 6.393 | 0.974 | 0.012 | 0.853 | 0.622 | 0.000 |
| always_strongest | max_utility | 14248 | 0.124 | 0.1220 | 3.058 | 0.974 | 0.012 | 0.853 | 0.757 | 0.000 |
| always_strongest | max_quality | 14248 | 0.981 | 0.0027 | 1.008 | 0.974 | 0.012 | 0.853 | 0.853 | 0.000 |
| always_strongest | all | 42744 | 0.393 | 0.0519 | 2.033 | 0.974 | 0.012 | 0.853 | 0.744 | 0.000 |
| always_cheapest | cheapest_above_threshold | 14248 | 0.527 | 0.1456 | 0.188 | 0.731 | 0.392 | 0.451 | 0.622 | 0.001 |
| always_cheapest | max_utility | 14248 | 0.183 | 0.2366 | 0.090 | 0.731 | 0.392 | 0.451 | 0.757 | 0.001 |
| always_cheapest | max_quality | 14248 | 0.011 | 0.1173 | 0.029 | 0.731 | 0.392 | 0.451 | 0.853 | 0.001 |
| always_cheapest | all | 42744 | 0.240 | 0.1665 | 0.060 | 0.731 | 0.392 | 0.451 | 0.744 | 0.001 |
