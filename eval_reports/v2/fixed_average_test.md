# Eval: `fixed_average` on `test` (n=364)

Sources: {'minimal-pair': 78, 'swe-rebench': 53, 'swe-smith': 20, 'synthetic': 148, 'wildchat': 65}  
Latency (batch 1): p50 0.0 ms, p95 0.0 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.310 / 0.442 / 0.034 |
| difficulty | MAE / Spearman / QWK / ECE | 1.696 / - / 0.000 / 0.004 |
| skills | mean MAE / mean Spearman / mean ECE | 1.831 / - / 0.120 |
| flags | F1 macro / AUROC macro / ECE | 0.421 / 0.500 / 0.015 |
| checklist | F1 macro / micro / AUROC | 0.221 / 0.570 / 0.500 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.355 / 0.755 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 78 | 0.282 | 1.640 | - | 0.447 | 0.225 |
| swe-rebench | 53 | 0.566 | 1.001 | - | 0.523 | 0.257 |
| swe-smith | 20 | 1.000 | 1.245 | - | 0.380 | 0.442 |
| synthetic | 148 | 0.243 | 1.665 | - | 0.483 | 0.238 |
| wildchat | 65 | 0.077 | 2.537 | - | 0.207 | 0.130 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 18170 | 0.396 | -0.0466 | 0.692 | 0.797 | 0.286 | 0.639 | 0.550 | 0.000 |
| predicted | max_utility | 18170 | 0.749 | -0.0038 | 0.599 | 0.781 | 0.307 | 0.618 | 0.632 | 0.000 |
| predicted | max_quality | 18170 | 0.982 | 0.0012 | 1.007 | 0.830 | 0.236 | 0.696 | 0.696 | 0.000 |
| predicted | all | 54510 | 0.709 | -0.0164 | 0.811 | 0.802 | 0.276 | 0.651 | 0.626 | 0.000 |
| always_strongest | cheapest_above_threshold | 18170 | 0.388 | 0.0187 | 1.628 | 0.821 | 0.243 | 0.690 | 0.550 | 0.014 |
| always_strongest | max_utility | 18170 | 0.401 | 0.0939 | 1.743 | 0.821 | 0.243 | 0.690 | 0.632 | 0.014 |
| always_strongest | max_quality | 18170 | 0.964 | 0.0157 | 1.006 | 0.821 | 0.243 | 0.690 | 0.696 | 0.014 |
| always_strongest | all | 54510 | 0.584 | 0.0428 | 1.375 | 0.821 | 0.243 | 0.690 | 0.626 | 0.014 |
| always_cheapest | cheapest_above_threshold | 18170 | 0.165 | 0.3111 | 0.015 | 0.400 | 0.760 | 0.218 | 0.550 | 0.082 |
| always_cheapest | max_utility | 18170 | 0.059 | 0.3863 | 0.016 | 0.400 | 0.760 | 0.218 | 0.632 | 0.082 |
| always_cheapest | max_quality | 18170 | 0.014 | 0.3081 | 0.009 | 0.400 | 0.760 | 0.218 | 0.696 | 0.082 |
| always_cheapest | all | 54510 | 0.079 | 0.3352 | 0.012 | 0.400 | 0.760 | 0.218 | 0.626 | 0.082 |
