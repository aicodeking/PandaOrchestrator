# Eval: `torch:checkpoints/v2_32_a03c/best` on `test` (n=120)

Sources: {'minimal-pair': 15, 'swe-rebench': 11, 'synthetic': 83, 'wildchat': 11}  
Latency (batch 1): p50 63.176 ms, p95 198.865 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.633 / 0.800 / 0.112 |
| difficulty | MAE / Spearman / QWK / ECE | 0.909 / 0.852 / 0.797 / 0.049 |
| skills | mean MAE / mean Spearman / mean ECE | 1.171 / 0.760 / 0.115 |
| flags | F1 macro / AUROC macro / ECE | 0.817 / 0.926 / 0.054 |
| checklist | F1 macro / micro / AUROC | 0.703 / 0.804 / 0.881 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.203 / 0.858 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 15 | 0.533 | 0.547 | 0.890 | 0.778 | 0.692 |
| swe-rebench | 11 | 0.818 | 0.497 | 0.827 | 0.691 | 0.393 |
| synthetic | 83 | 0.639 | 0.983 | 0.791 | 0.859 | 0.697 |
| wildchat | 11 | 0.545 | 1.261 | 0.527 | 0.150 | 0.302 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 5994 | 0.736 | 0.0076 | 0.973 | 0.647 | 0.515 | 0.487 | 0.495 | 0.000 |
| predicted | max_utility | 5994 | 0.836 | -0.0031 | 0.851 | 0.667 | 0.480 | 0.530 | 0.545 | 0.000 |
| predicted | max_quality | 5994 | 0.986 | 0.0005 | 1.008 | 0.704 | 0.424 | 0.592 | 0.592 | 0.000 |
| predicted | all | 17982 | 0.853 | 0.0017 | 0.952 | 0.673 | 0.473 | 0.536 | 0.544 | 0.000 |
| always_strongest | cheapest_above_threshold | 5994 | 0.555 | 0.0233 | 1.393 | 0.698 | 0.428 | 0.587 | 0.495 | 0.013 |
| always_strongest | max_utility | 5994 | 0.552 | 0.0716 | 1.442 | 0.698 | 0.428 | 0.587 | 0.545 | 0.013 |
| always_strongest | max_quality | 5994 | 0.962 | 0.0153 | 1.012 | 0.698 | 0.428 | 0.587 | 0.592 | 0.013 |
| always_strongest | all | 17982 | 0.690 | 0.0367 | 1.250 | 0.698 | 0.428 | 0.587 | 0.544 | 0.013 |
| always_cheapest | cheapest_above_threshold | 5994 | 0.096 | 0.2779 | 0.013 | 0.266 | 0.870 | 0.145 | 0.495 | 0.071 |
| always_cheapest | max_utility | 5994 | 0.042 | 0.3262 | 0.013 | 0.266 | 0.870 | 0.145 | 0.545 | 0.071 |
| always_cheapest | max_quality | 5994 | 0.014 | 0.2699 | 0.009 | 0.266 | 0.870 | 0.145 | 0.592 | 0.071 |
| always_cheapest | all | 17982 | 0.051 | 0.2913 | 0.011 | 0.266 | 0.870 | 0.145 | 0.544 | 0.071 |
