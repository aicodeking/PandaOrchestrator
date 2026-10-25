# Eval: `onnx:artifacts/r150m` on `gold` (n=285)

Sources: {'swe-rebench': 92, 'swe-smith': 23, 'wildchat': 170}  
Latency (batch 1): p50 29.33 ms, p95 99.387 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.667 / 0.874 / 0.169 |
| difficulty | MAE / Spearman / QWK / ECE | 0.833 / 0.752 / 0.696 / 0.035 |
| skills | mean MAE / mean Spearman / mean ECE | 0.694 / 0.650 / 0.159 |
| flags | F1 macro / AUROC macro / ECE | 0.535 / 0.868 / 0.053 |
| checklist | F1 macro / micro / AUROC | 0.512 / 0.745 / 0.881 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.233 / 0.740 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | 0.104 / 0.004 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 92 | 0.870 | 0.704 | 0.565 | 0.523 | 0.362 |
| swe-smith | 23 | 1.000 | 0.672 | 0.716 | 0.838 | 0.724 |
| wildchat | 170 | 0.512 | 0.924 | 0.694 | 0.237 | 0.407 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 14248 | 0.778 | 0.0071 | 0.761 | 0.882 | 0.125 | 0.610 | 0.622 | 0.000 |
| predicted | max_utility | 14248 | 0.886 | 0.0025 | 0.924 | 0.944 | 0.040 | 0.753 | 0.757 | 0.000 |
| predicted | max_quality | 14248 | 0.986 | 0.0018 | 1.006 | 0.974 | 0.012 | 0.853 | 0.853 | 0.000 |
| predicted | all | 42744 | 0.883 | 0.0038 | 0.962 | 0.933 | 0.059 | 0.739 | 0.744 | 0.000 |
| always_strongest | cheapest_above_threshold | 14248 | 0.074 | 0.0310 | 6.393 | 0.974 | 0.012 | 0.853 | 0.622 | 0.000 |
| always_strongest | max_utility | 14248 | 0.124 | 0.1220 | 3.058 | 0.974 | 0.012 | 0.853 | 0.757 | 0.000 |
| always_strongest | max_quality | 14248 | 0.981 | 0.0027 | 1.008 | 0.974 | 0.012 | 0.853 | 0.853 | 0.000 |
| always_strongest | all | 42744 | 0.393 | 0.0519 | 2.033 | 0.974 | 0.012 | 0.853 | 0.744 | 0.000 |
| always_cheapest | cheapest_above_threshold | 14248 | 0.527 | 0.1456 | 0.188 | 0.731 | 0.392 | 0.451 | 0.622 | 0.001 |
| always_cheapest | max_utility | 14248 | 0.183 | 0.2366 | 0.090 | 0.731 | 0.392 | 0.451 | 0.757 | 0.001 |
| always_cheapest | max_quality | 14248 | 0.011 | 0.1173 | 0.029 | 0.731 | 0.392 | 0.451 | 0.853 | 0.001 |
| always_cheapest | all | 42744 | 0.240 | 0.1665 | 0.060 | 0.731 | 0.392 | 0.451 | 0.744 | 0.001 |
