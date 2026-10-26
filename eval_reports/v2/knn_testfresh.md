# Eval: `knn` on `test` (n=120)

Sources: {'minimal-pair': 15, 'swe-rebench': 11, 'synthetic': 83, 'wildchat': 11}  
Latency (batch 1): p50 13.125 ms, p95 25.98 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.483 / 0.617 / 0.135 |
| difficulty | MAE / Spearman / QWK / ECE | 1.117 / 0.749 / 0.613 / 0.088 |
| skills | mean MAE / mean Spearman / mean ECE | 1.329 / 0.699 / 0.109 |
| flags | F1 macro / AUROC macro / ECE | 0.546 / 0.821 / 0.091 |
| checklist | F1 macro / micro / AUROC | 0.594 / 0.755 / 0.802 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.272 / 0.867 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 15 | 0.400 | 0.934 | 0.737 | 0.548 | 0.540 |
| swe-rebench | 11 | 0.545 | 0.911 | 0.554 | 0.664 | 0.339 |
| synthetic | 83 | 0.494 | 1.118 | 0.582 | 0.561 | 0.609 |
| wildchat | 11 | 0.455 | 1.568 | 0.036 | 0.067 | 0.236 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 5994 | 0.674 | -0.0150 | 1.116 | 0.685 | 0.450 | 0.544 | 0.495 | 0.000 |
| predicted | max_utility | 5994 | 0.820 | 0.0001 | 0.883 | 0.674 | 0.469 | 0.541 | 0.545 | 0.000 |
| predicted | max_quality | 5994 | 0.986 | 0.0005 | 1.011 | 0.705 | 0.424 | 0.592 | 0.592 | 0.000 |
| predicted | all | 17982 | 0.826 | -0.0048 | 1.006 | 0.688 | 0.448 | 0.559 | 0.544 | 0.000 |
| always_strongest | cheapest_above_threshold | 5994 | 0.555 | 0.0233 | 1.393 | 0.698 | 0.428 | 0.587 | 0.495 | 0.013 |
| always_strongest | max_utility | 5994 | 0.552 | 0.0716 | 1.442 | 0.698 | 0.428 | 0.587 | 0.545 | 0.013 |
| always_strongest | max_quality | 5994 | 0.962 | 0.0153 | 1.012 | 0.698 | 0.428 | 0.587 | 0.592 | 0.013 |
| always_strongest | all | 17982 | 0.690 | 0.0367 | 1.250 | 0.698 | 0.428 | 0.587 | 0.544 | 0.013 |
| always_cheapest | cheapest_above_threshold | 5994 | 0.096 | 0.2779 | 0.013 | 0.266 | 0.870 | 0.145 | 0.495 | 0.071 |
| always_cheapest | max_utility | 5994 | 0.042 | 0.3262 | 0.013 | 0.266 | 0.870 | 0.145 | 0.545 | 0.071 |
| always_cheapest | max_quality | 5994 | 0.014 | 0.2699 | 0.009 | 0.266 | 0.870 | 0.145 | 0.592 | 0.071 |
| always_cheapest | all | 17982 | 0.051 | 0.2913 | 0.011 | 0.266 | 0.870 | 0.145 | 0.544 | 0.071 |
