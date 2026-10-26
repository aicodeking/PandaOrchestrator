# Eval: `torch:checkpoints/v2_32_a03c/best` on `test` (n=364)

Sources: {'minimal-pair': 78, 'swe-rebench': 53, 'swe-smith': 20, 'synthetic': 148, 'wildchat': 65}  
Latency (batch 1): p50 80.516 ms, p95 282.381 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.734 / 0.871 / 0.035 |
| difficulty | MAE / Spearman / QWK / ECE | 0.856 / 0.853 / 0.814 / 0.031 |
| skills | mean MAE / mean Spearman / mean ECE | 0.894 / 0.762 / 0.102 |
| flags | F1 macro / AUROC macro / ECE | 0.781 / 0.927 / 0.036 |
| checklist | F1 macro / micro / AUROC | 0.701 / 0.795 / 0.903 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.196 / 0.849 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 78 | 0.667 | 0.750 | 0.863 | 0.767 | 0.724 |
| swe-rebench | 53 | 0.811 | 0.856 | 0.256 | 0.576 | 0.377 |
| swe-smith | 20 | 1.000 | 0.632 | 0.624 | 0.444 | 0.455 |
| synthetic | 148 | 0.723 | 0.888 | 0.839 | 0.855 | 0.718 |
| wildchat | 65 | 0.692 | 0.977 | 0.629 | 0.202 | 0.378 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 18170 | 0.690 | 0.0120 | 0.938 | 0.746 | 0.383 | 0.530 | 0.550 | 0.000 |
| predicted | max_utility | 18170 | 0.874 | -0.0012 | 0.863 | 0.792 | 0.301 | 0.621 | 0.632 | 0.000 |
| predicted | max_quality | 18170 | 0.991 | 0.0003 | 1.004 | 0.830 | 0.236 | 0.696 | 0.696 | 0.000 |
| predicted | all | 54510 | 0.852 | 0.0037 | 0.948 | 0.789 | 0.307 | 0.616 | 0.626 | 0.000 |
| always_strongest | cheapest_above_threshold | 18170 | 0.388 | 0.0187 | 1.628 | 0.821 | 0.243 | 0.690 | 0.550 | 0.014 |
| always_strongest | max_utility | 18170 | 0.401 | 0.0939 | 1.743 | 0.821 | 0.243 | 0.690 | 0.632 | 0.014 |
| always_strongest | max_quality | 18170 | 0.964 | 0.0157 | 1.006 | 0.821 | 0.243 | 0.690 | 0.696 | 0.014 |
| always_strongest | all | 54510 | 0.584 | 0.0428 | 1.375 | 0.821 | 0.243 | 0.690 | 0.626 | 0.014 |
| always_cheapest | cheapest_above_threshold | 18170 | 0.165 | 0.3111 | 0.015 | 0.400 | 0.760 | 0.218 | 0.550 | 0.082 |
| always_cheapest | max_utility | 18170 | 0.059 | 0.3863 | 0.016 | 0.400 | 0.760 | 0.218 | 0.632 | 0.082 |
| always_cheapest | max_quality | 18170 | 0.014 | 0.3081 | 0.009 | 0.400 | 0.760 | 0.218 | 0.696 | 0.082 |
| always_cheapest | all | 54510 | 0.079 | 0.3352 | 0.012 | 0.400 | 0.760 | 0.218 | 0.626 | 0.082 |
