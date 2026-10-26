# Eval: `torch:checkpoints/v2_32_rc1c/best` on `test` (n=120)

Sources: {'minimal-pair': 15, 'swe-rebench': 11, 'synthetic': 83, 'wildchat': 11}  
Latency (batch 1): p50 82.241 ms, p95 196.243 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.683 / 0.825 / 0.091 |
| difficulty | MAE / Spearman / QWK / ECE | 0.898 / 0.860 / 0.805 / 0.026 |
| skills | mean MAE / mean Spearman / mean ECE | 1.190 / 0.761 / 0.103 |
| flags | F1 macro / AUROC macro / ECE | 0.802 / 0.932 / 0.046 |
| checklist | F1 macro / micro / AUROC | 0.698 / 0.805 / 0.879 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.200 / 0.783 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 15 | 0.467 | 0.497 | 0.946 | 0.789 | 0.664 |
| swe-rebench | 11 | 0.818 | 0.628 | 0.746 | 0.691 | 0.361 |
| synthetic | 83 | 0.723 | 0.987 | 0.798 | 0.818 | 0.698 |
| wildchat | 11 | 0.545 | 1.042 | 0.736 | 0.071 | 0.319 |

## Routing (cards: cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 5994 | 0.745 | 0.0018 | 0.972 | 0.652 | 0.515 | 0.490 | 0.495 | 0.000 |
| predicted | max_utility | 5994 | 0.831 | -0.0044 | 0.831 | 0.664 | 0.482 | 0.527 | 0.545 | 0.000 |
| predicted | max_quality | 5994 | 0.985 | 0.0005 | 1.008 | 0.704 | 0.424 | 0.592 | 0.592 | 0.000 |
| predicted | all | 17982 | 0.854 | -0.0007 | 0.946 | 0.674 | 0.474 | 0.536 | 0.544 | 0.000 |
| always_strongest | cheapest_above_threshold | 5994 | 0.555 | 0.0233 | 1.393 | 0.698 | 0.428 | 0.587 | 0.495 | 0.013 |
| always_strongest | max_utility | 5994 | 0.552 | 0.0716 | 1.442 | 0.698 | 0.428 | 0.587 | 0.545 | 0.013 |
| always_strongest | max_quality | 5994 | 0.962 | 0.0153 | 1.012 | 0.698 | 0.428 | 0.587 | 0.592 | 0.013 |
| always_strongest | all | 17982 | 0.690 | 0.0367 | 1.250 | 0.698 | 0.428 | 0.587 | 0.544 | 0.013 |
| always_cheapest | cheapest_above_threshold | 5994 | 0.096 | 0.2779 | 0.013 | 0.266 | 0.870 | 0.145 | 0.495 | 0.071 |
| always_cheapest | max_utility | 5994 | 0.042 | 0.3262 | 0.013 | 0.266 | 0.870 | 0.145 | 0.545 | 0.071 |
| always_cheapest | max_quality | 5994 | 0.014 | 0.2699 | 0.009 | 0.266 | 0.870 | 0.145 | 0.592 | 0.071 |
| always_cheapest | all | 17982 | 0.051 | 0.2913 | 0.011 | 0.266 | 0.870 | 0.145 | 0.544 | 0.071 |
