# Eval: `onnx:artifacts/s32m_soup` on `test` (n=300)

Sources: {'minimal-pair': 89, 'swe-rebench': 53, 'swe-smith': 7, 'synthetic': 68, 'wildchat': 83}  
Latency (batch 1): p50 7.528 ms, p95 19.236 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.680 / 0.800 / 0.060 |
| difficulty | MAE / Spearman / QWK / ECE | 0.825 / 0.828 / 0.805 / 0.054 |
| skills | mean MAE / mean Spearman / mean ECE | 0.996 / 0.710 / 0.116 |
| flags | F1 macro / AUROC macro / ECE | 0.744 / 0.898 / 0.045 |
| checklist | F1 macro / micro / AUROC | 0.603 / 0.751 / 0.881 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.220 / 0.793 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 89 | 0.674 | 0.810 | 0.876 | 0.776 | 0.627 |
| swe-rebench | 53 | 0.811 | 0.795 | 0.491 | 0.564 | 0.381 |
| swe-smith | 7 | 1.000 | 0.913 | 0.704 | 0.583 | 0.500 |
| synthetic | 68 | 0.647 | 0.617 | 0.659 | 0.748 | 0.625 |
| wildchat | 83 | 0.602 | 1.022 | 0.642 | 0.268 | 0.282 |

## Routing (cards: cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 14978 | 0.701 | 0.0033 | 0.996 | 0.829 | 0.233 | 0.621 | 0.623 | 0.002 |
| predicted | max_utility | 14978 | 0.852 | 0.0026 | 0.940 | 0.863 | 0.190 | 0.703 | 0.710 | 0.000 |
| predicted | max_quality | 14978 | 0.989 | 0.0012 | 1.012 | 0.903 | 0.118 | 0.793 | 0.793 | 0.000 |
| predicted | all | 44934 | 0.847 | 0.0024 | 0.990 | 0.865 | 0.181 | 0.706 | 0.709 | 0.001 |
| always_strongest | cheapest_above_threshold | 14978 | 0.260 | 0.0357 | 1.805 | 0.902 | 0.120 | 0.792 | 0.623 | 0.003 |
| always_strongest | max_utility | 14978 | 0.249 | 0.1019 | 1.903 | 0.902 | 0.120 | 0.792 | 0.710 | 0.003 |
| always_strongest | max_quality | 14978 | 0.985 | 0.0044 | 1.013 | 0.902 | 0.120 | 0.792 | 0.793 | 0.003 |
| always_strongest | all | 44934 | 0.498 | 0.0474 | 1.452 | 0.902 | 0.120 | 0.792 | 0.709 | 0.003 |
| always_cheapest | cheapest_above_threshold | 14978 | 0.345 | 0.2248 | 0.055 | 0.555 | 0.608 | 0.348 | 0.623 | 0.046 |
| always_cheapest | max_utility | 14978 | 0.137 | 0.2910 | 0.058 | 0.555 | 0.608 | 0.348 | 0.710 | 0.046 |
| always_cheapest | max_quality | 14978 | 0.013 | 0.1936 | 0.031 | 0.555 | 0.608 | 0.348 | 0.793 | 0.046 |
| always_cheapest | all | 44934 | 0.165 | 0.2365 | 0.045 | 0.555 | 0.608 | 0.348 | 0.709 | 0.046 |
