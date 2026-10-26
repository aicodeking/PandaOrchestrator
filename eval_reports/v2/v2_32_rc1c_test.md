# Eval: `torch:checkpoints/v2_32_rc1c/best` on `test` (n=364)

Sources: {'minimal-pair': 78, 'swe-rebench': 53, 'swe-smith': 20, 'synthetic': 148, 'wildchat': 65}  
Latency (batch 1): p50 77.05 ms, p95 289.874 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.734 / 0.849 / 0.049 |
| difficulty | MAE / Spearman / QWK / ECE | 0.865 / 0.853 / 0.811 / 0.021 |
| skills | mean MAE / mean Spearman / mean ECE | 0.911 / 0.761 / 0.105 |
| flags | F1 macro / AUROC macro / ECE | 0.761 / 0.922 / 0.032 |
| checklist | F1 macro / micro / AUROC | 0.694 / 0.792 / 0.900 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.197 / 0.766 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 78 | 0.641 | 0.835 | 0.841 | 0.758 | 0.704 |
| swe-rebench | 53 | 0.792 | 0.856 | 0.219 | 0.495 | 0.339 |
| swe-smith | 20 | 1.000 | 0.743 | 0.563 | 0.444 | 0.497 |
| synthetic | 148 | 0.743 | 0.881 | 0.841 | 0.825 | 0.711 |
| wildchat | 65 | 0.692 | 0.906 | 0.665 | 0.164 | 0.399 |

## Routing (cards: cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 18170 | 0.694 | 0.0096 | 0.920 | 0.748 | 0.380 | 0.531 | 0.550 | 0.000 |
| predicted | max_utility | 18170 | 0.869 | -0.0014 | 0.837 | 0.791 | 0.301 | 0.619 | 0.632 | 0.000 |
| predicted | max_quality | 18170 | 0.991 | 0.0002 | 1.004 | 0.830 | 0.236 | 0.696 | 0.696 | 0.000 |
| predicted | all | 54510 | 0.851 | 0.0028 | 0.936 | 0.789 | 0.306 | 0.615 | 0.626 | 0.000 |
| always_strongest | cheapest_above_threshold | 18170 | 0.388 | 0.0187 | 1.628 | 0.821 | 0.243 | 0.690 | 0.550 | 0.014 |
| always_strongest | max_utility | 18170 | 0.401 | 0.0939 | 1.743 | 0.821 | 0.243 | 0.690 | 0.632 | 0.014 |
| always_strongest | max_quality | 18170 | 0.964 | 0.0157 | 1.006 | 0.821 | 0.243 | 0.690 | 0.696 | 0.014 |
| always_strongest | all | 54510 | 0.584 | 0.0428 | 1.375 | 0.821 | 0.243 | 0.690 | 0.626 | 0.014 |
| always_cheapest | cheapest_above_threshold | 18170 | 0.165 | 0.3111 | 0.015 | 0.400 | 0.760 | 0.218 | 0.550 | 0.082 |
| always_cheapest | max_utility | 18170 | 0.059 | 0.3863 | 0.016 | 0.400 | 0.760 | 0.218 | 0.632 | 0.082 |
| always_cheapest | max_quality | 18170 | 0.014 | 0.3081 | 0.009 | 0.400 | 0.760 | 0.218 | 0.696 | 0.082 |
| always_cheapest | all | 54510 | 0.079 | 0.3352 | 0.012 | 0.400 | 0.760 | 0.218 | 0.626 | 0.082 |
