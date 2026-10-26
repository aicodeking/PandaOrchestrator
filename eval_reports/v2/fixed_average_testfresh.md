# Eval: `fixed_average` on `test` (n=120)

Sources: {'minimal-pair': 15, 'swe-rebench': 11, 'synthetic': 83, 'wildchat': 11}  
Latency (batch 1): p50 0.0 ms, p95 0.001 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.267 / 0.450 / 0.078 |
| difficulty | MAE / Spearman / QWK / ECE | 1.910 / - / 0.000 / 0.049 |
| skills | mean MAE / mean Spearman / mean ECE | 2.085 / - / 0.048 |
| flags | F1 macro / AUROC macro / ECE | 0.484 / 0.500 / 0.083 |
| checklist | F1 macro / micro / AUROC | 0.239 / 0.584 / 0.500 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.399 / 0.717 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 15 | 0.133 | 1.614 | - | 0.501 | 0.245 |
| swe-rebench | 11 | 0.273 | 1.050 | - | 0.693 | 0.288 |
| synthetic | 83 | 0.277 | 2.041 | - | 0.506 | 0.246 |
| wildchat | 11 | 0.364 | 2.189 | - | 0.181 | 0.214 |

## Routing (cards: cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 5994 | 0.448 | -0.0324 | 0.596 | 0.657 | 0.485 | 0.527 | 0.495 | 0.000 |
| predicted | max_utility | 5994 | 0.655 | -0.0170 | 0.484 | 0.637 | 0.496 | 0.505 | 0.545 | 0.000 |
| predicted | max_quality | 5994 | 0.976 | 0.0017 | 1.014 | 0.705 | 0.424 | 0.592 | 0.592 | 0.000 |
| predicted | all | 17982 | 0.693 | -0.0159 | 0.736 | 0.666 | 0.468 | 0.541 | 0.544 | 0.000 |
| always_strongest | cheapest_above_threshold | 5994 | 0.555 | 0.0233 | 1.393 | 0.698 | 0.428 | 0.587 | 0.495 | 0.013 |
| always_strongest | max_utility | 5994 | 0.552 | 0.0716 | 1.442 | 0.698 | 0.428 | 0.587 | 0.545 | 0.013 |
| always_strongest | max_quality | 5994 | 0.962 | 0.0153 | 1.012 | 0.698 | 0.428 | 0.587 | 0.592 | 0.013 |
| always_strongest | all | 17982 | 0.690 | 0.0367 | 1.250 | 0.698 | 0.428 | 0.587 | 0.544 | 0.013 |
| always_cheapest | cheapest_above_threshold | 5994 | 0.096 | 0.2779 | 0.013 | 0.266 | 0.870 | 0.145 | 0.495 | 0.071 |
| always_cheapest | max_utility | 5994 | 0.042 | 0.3262 | 0.013 | 0.266 | 0.870 | 0.145 | 0.545 | 0.071 |
| always_cheapest | max_quality | 5994 | 0.014 | 0.2699 | 0.009 | 0.266 | 0.870 | 0.145 | 0.592 | 0.071 |
| always_cheapest | all | 17982 | 0.051 | 0.2913 | 0.011 | 0.266 | 0.870 | 0.145 | 0.544 | 0.071 |
