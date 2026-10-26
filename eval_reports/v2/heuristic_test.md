# Eval: `heuristic` on `test` (n=364)

Sources: {'minimal-pair': 78, 'swe-rebench': 53, 'swe-smith': 20, 'synthetic': 148, 'wildchat': 65}  
Latency (batch 1): p50 0.263 ms, p95 1.358 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.407 / 0.646 / 0.165 |
| difficulty | MAE / Spearman / QWK / ECE | 1.768 / 0.683 / 0.444 / 0.197 |
| skills | mean MAE / mean Spearman / mean ECE | 1.854 / 0.410 / 0.228 |
| flags | F1 macro / AUROC macro / ECE | 0.579 / 0.791 / 0.158 |
| checklist | F1 macro / micro / AUROC | 0.368 / 0.417 / 0.710 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.365 / 0.717 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 78 | 0.346 | 1.894 | 0.721 | 0.608 | 0.362 |
| swe-rebench | 53 | 0.434 | 1.783 | 0.170 | 0.438 | 0.254 |
| swe-smith | 20 | 0.550 | 1.379 | -0.009 | 0.333 | 0.319 |
| synthetic | 148 | 0.392 | 1.950 | 0.562 | 0.549 | 0.343 |
| wildchat | 65 | 0.446 | 1.310 | 0.344 | 0.120 | 0.145 |

## Routing (cards: cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 18170 | 0.465 | 0.0999 | 0.480 | 0.606 | 0.595 | 0.387 | 0.550 | 0.000 |
| predicted | max_utility | 18170 | 0.757 | -0.0017 | 0.619 | 0.766 | 0.332 | 0.592 | 0.632 | 0.000 |
| predicted | max_quality | 18170 | 0.982 | 0.0005 | 1.004 | 0.829 | 0.237 | 0.696 | 0.696 | 0.000 |
| predicted | all | 54510 | 0.735 | 0.0329 | 0.755 | 0.734 | 0.388 | 0.558 | 0.626 | 0.000 |
| always_strongest | cheapest_above_threshold | 18170 | 0.388 | 0.0187 | 1.628 | 0.821 | 0.243 | 0.690 | 0.550 | 0.014 |
| always_strongest | max_utility | 18170 | 0.401 | 0.0939 | 1.743 | 0.821 | 0.243 | 0.690 | 0.632 | 0.014 |
| always_strongest | max_quality | 18170 | 0.964 | 0.0157 | 1.006 | 0.821 | 0.243 | 0.690 | 0.696 | 0.014 |
| always_strongest | all | 54510 | 0.584 | 0.0428 | 1.375 | 0.821 | 0.243 | 0.690 | 0.626 | 0.014 |
| always_cheapest | cheapest_above_threshold | 18170 | 0.165 | 0.3111 | 0.015 | 0.400 | 0.760 | 0.218 | 0.550 | 0.082 |
| always_cheapest | max_utility | 18170 | 0.059 | 0.3863 | 0.016 | 0.400 | 0.760 | 0.218 | 0.632 | 0.082 |
| always_cheapest | max_quality | 18170 | 0.014 | 0.3081 | 0.009 | 0.400 | 0.760 | 0.218 | 0.696 | 0.082 |
| always_cheapest | all | 54510 | 0.079 | 0.3352 | 0.012 | 0.400 | 0.760 | 0.218 | 0.626 | 0.082 |
