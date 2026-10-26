# Eval: `onnx:artifacts/r150m` on `test` (n=300)

Sources: {'minimal-pair': 89, 'swe-rebench': 53, 'swe-smith': 7, 'synthetic': 68, 'wildchat': 83}  
Latency (batch 1): p50 37.865 ms, p95 98.243 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.753 / 0.873 / 0.048 |
| difficulty | MAE / Spearman / QWK / ECE | 0.786 / 0.859 / 0.829 / 0.049 |
| skills | mean MAE / mean Spearman / mean ECE | 0.836 / 0.774 / 0.127 |
| flags | F1 macro / AUROC macro / ECE | 0.783 / 0.927 / 0.040 |
| checklist | F1 macro / micro / AUROC | 0.730 / 0.802 / 0.914 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.206 / 0.777 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 89 | 0.730 | 0.801 | 0.897 | 0.786 | 0.743 |
| swe-rebench | 53 | 0.868 | 0.857 | 0.448 | 0.570 | 0.456 |
| swe-smith | 7 | 1.000 | 0.506 | 0.889 | 0.667 | 0.717 |
| synthetic | 68 | 0.809 | 0.569 | 0.740 | 0.820 | 0.776 |
| wildchat | 83 | 0.639 | 0.927 | 0.732 | 0.347 | 0.447 |

## Routing (cards: cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 14978 | 0.710 | 0.0018 | 1.008 | 0.829 | 0.236 | 0.620 | 0.623 | 0.001 |
| predicted | max_utility | 14978 | 0.863 | 0.0024 | 0.952 | 0.864 | 0.189 | 0.703 | 0.710 | 0.000 |
| predicted | max_quality | 14978 | 0.989 | 0.0012 | 1.012 | 0.903 | 0.118 | 0.793 | 0.793 | 0.000 |
| predicted | all | 44934 | 0.854 | 0.0018 | 0.996 | 0.866 | 0.181 | 0.705 | 0.709 | 0.000 |
| always_strongest | cheapest_above_threshold | 14978 | 0.260 | 0.0357 | 1.805 | 0.902 | 0.120 | 0.792 | 0.623 | 0.003 |
| always_strongest | max_utility | 14978 | 0.249 | 0.1019 | 1.903 | 0.902 | 0.120 | 0.792 | 0.710 | 0.003 |
| always_strongest | max_quality | 14978 | 0.985 | 0.0044 | 1.013 | 0.902 | 0.120 | 0.792 | 0.793 | 0.003 |
| always_strongest | all | 44934 | 0.498 | 0.0474 | 1.452 | 0.902 | 0.120 | 0.792 | 0.709 | 0.003 |
| always_cheapest | cheapest_above_threshold | 14978 | 0.345 | 0.2248 | 0.055 | 0.555 | 0.608 | 0.348 | 0.623 | 0.046 |
| always_cheapest | max_utility | 14978 | 0.137 | 0.2910 | 0.058 | 0.555 | 0.608 | 0.348 | 0.710 | 0.046 |
| always_cheapest | max_quality | 14978 | 0.013 | 0.1936 | 0.031 | 0.555 | 0.608 | 0.348 | 0.793 | 0.046 |
| always_cheapest | all | 44934 | 0.165 | 0.2365 | 0.045 | 0.555 | 0.608 | 0.348 | 0.709 | 0.046 |
