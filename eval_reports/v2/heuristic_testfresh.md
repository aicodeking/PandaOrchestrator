# Eval: `heuristic` on `test` (n=120)

Sources: {'minimal-pair': 15, 'swe-rebench': 11, 'synthetic': 83, 'wildchat': 11}  
Latency (batch 1): p50 0.402 ms, p95 2.098 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.483 / 0.733 / 0.160 |
| difficulty | MAE / Spearman / QWK / ECE | 2.140 / 0.638 / 0.349 / 0.228 |
| skills | mean MAE / mean Spearman / mean ECE | 2.499 / 0.402 / 0.244 |
| flags | F1 macro / AUROC macro / ECE | 0.589 / 0.800 / 0.210 |
| checklist | F1 macro / micro / AUROC | 0.353 / 0.417 / 0.701 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.452 / 0.575 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 15 | 0.467 | 2.040 | 0.782 | 0.649 | 0.381 |
| swe-rebench | 11 | 0.455 | 1.449 | 0.191 | 0.383 | 0.206 |
| synthetic | 83 | 0.506 | 2.335 | 0.449 | 0.553 | 0.331 |
| wildchat | 11 | 0.364 | 1.492 | 0.109 | 0.133 | 0.176 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 5994 | 0.396 | 0.0783 | 0.461 | 0.488 | 0.715 | 0.326 | 0.495 | 0.001 |
| predicted | max_utility | 5994 | 0.645 | -0.0124 | 0.568 | 0.625 | 0.515 | 0.486 | 0.545 | 0.001 |
| predicted | max_quality | 5994 | 0.978 | 0.0008 | 1.008 | 0.704 | 0.425 | 0.591 | 0.592 | 0.001 |
| predicted | all | 17982 | 0.673 | 0.0222 | 0.717 | 0.605 | 0.551 | 0.468 | 0.544 | 0.001 |
| always_strongest | cheapest_above_threshold | 5994 | 0.555 | 0.0233 | 1.393 | 0.698 | 0.428 | 0.587 | 0.495 | 0.013 |
| always_strongest | max_utility | 5994 | 0.552 | 0.0716 | 1.442 | 0.698 | 0.428 | 0.587 | 0.545 | 0.013 |
| always_strongest | max_quality | 5994 | 0.962 | 0.0153 | 1.012 | 0.698 | 0.428 | 0.587 | 0.592 | 0.013 |
| always_strongest | all | 17982 | 0.690 | 0.0367 | 1.250 | 0.698 | 0.428 | 0.587 | 0.544 | 0.013 |
| always_cheapest | cheapest_above_threshold | 5994 | 0.096 | 0.2779 | 0.013 | 0.266 | 0.870 | 0.145 | 0.495 | 0.071 |
| always_cheapest | max_utility | 5994 | 0.042 | 0.3262 | 0.013 | 0.266 | 0.870 | 0.145 | 0.545 | 0.071 |
| always_cheapest | max_quality | 5994 | 0.014 | 0.2699 | 0.009 | 0.266 | 0.870 | 0.145 | 0.592 | 0.071 |
| always_cheapest | all | 17982 | 0.051 | 0.2913 | 0.011 | 0.266 | 0.870 | 0.145 | 0.544 | 0.071 |
