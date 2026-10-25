# Eval: `heuristic` on `gold` (n=285)

Sources: {'swe-rebench': 92, 'swe-smith': 23, 'wildchat': 170}  
Latency (batch 1): p50 0.582 ms, p95 5.368 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.498 / 0.660 / 0.202 |
| difficulty | MAE / Spearman / QWK / ECE | 1.342 / 0.566 / 0.360 / 0.127 |
| skills | mean MAE / mean Spearman / mean ECE | 1.237 / 0.309 / 0.278 |
| flags | F1 macro / AUROC macro / ECE | 0.266 / 0.641 / 0.125 |
| checklist | F1 macro / micro / AUROC | 0.248 / 0.373 / 0.676 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.271 / 0.842 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | 0.057 / 0.004 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 92 | 0.543 | 1.776 | 0.447 | 0.344 | 0.232 |
| swe-smith | 23 | 0.696 | 1.533 | 0.465 | 0.333 | 0.283 |
| wildchat | 170 | 0.447 | 1.081 | 0.555 | 0.095 | 0.173 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 14248 | 0.703 | 0.0715 | 0.342 | 0.811 | 0.267 | 0.533 | 0.622 | 0.000 |
| predicted | max_utility | 14248 | 0.818 | 0.0060 | 0.712 | 0.933 | 0.060 | 0.733 | 0.757 | 0.000 |
| predicted | max_quality | 14248 | 0.981 | 0.0021 | 1.004 | 0.973 | 0.013 | 0.853 | 0.853 | 0.000 |
| predicted | all | 42744 | 0.834 | 0.0265 | 0.870 | 0.906 | 0.113 | 0.706 | 0.744 | 0.000 |
| always_strongest | cheapest_above_threshold | 14248 | 0.074 | 0.0310 | 6.393 | 0.974 | 0.012 | 0.853 | 0.622 | 0.000 |
| always_strongest | max_utility | 14248 | 0.124 | 0.1220 | 3.058 | 0.974 | 0.012 | 0.853 | 0.757 | 0.000 |
| always_strongest | max_quality | 14248 | 0.981 | 0.0027 | 1.008 | 0.974 | 0.012 | 0.853 | 0.853 | 0.000 |
| always_strongest | all | 42744 | 0.393 | 0.0519 | 2.033 | 0.974 | 0.012 | 0.853 | 0.744 | 0.000 |
| always_cheapest | cheapest_above_threshold | 14248 | 0.527 | 0.1456 | 0.188 | 0.731 | 0.392 | 0.451 | 0.622 | 0.001 |
| always_cheapest | max_utility | 14248 | 0.183 | 0.2366 | 0.090 | 0.731 | 0.392 | 0.451 | 0.757 | 0.001 |
| always_cheapest | max_quality | 14248 | 0.011 | 0.1173 | 0.029 | 0.731 | 0.392 | 0.451 | 0.853 | 0.001 |
| always_cheapest | all | 42744 | 0.240 | 0.1665 | 0.060 | 0.731 | 0.392 | 0.451 | 0.744 | 0.001 |
