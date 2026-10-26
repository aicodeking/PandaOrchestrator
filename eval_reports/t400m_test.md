# Eval: `onnx:artifacts/t400m` on `test` (n=300)

Sources: {'minimal-pair': 89, 'swe-rebench': 53, 'swe-smith': 7, 'synthetic': 68, 'wildchat': 83}  
Latency (batch 1): p50 610.818 ms, p95 1389.013 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.720 / 0.840 / 0.060 |
| difficulty | MAE / Spearman / QWK / ECE | 0.860 / 0.823 / 0.798 / 0.017 |
| skills | mean MAE / mean Spearman / mean ECE | 1.015 / 0.699 / 0.126 |
| flags | F1 macro / AUROC macro / ECE | 0.741 / 0.901 / 0.040 |
| checklist | F1 macro / micro / AUROC | 0.580 / 0.737 / 0.870 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.206 / 0.767 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 89 | 0.742 | 0.877 | 0.860 | 0.764 | 0.581 |
| swe-rebench | 53 | 0.849 | 0.814 | 0.547 | 0.543 | 0.386 |
| swe-smith | 7 | 1.000 | 0.987 | 0.074 | 0.500 | 0.527 |
| synthetic | 68 | 0.721 | 0.725 | 0.573 | 0.753 | 0.608 |
| wildchat | 83 | 0.590 | 0.971 | 0.720 | 0.214 | 0.262 |

## Routing (cards: cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 14978 | 0.697 | 0.0149 | 1.035 | 0.816 | 0.262 | 0.603 | 0.623 | 0.001 |
| predicted | max_utility | 14978 | 0.850 | 0.0026 | 0.948 | 0.862 | 0.191 | 0.700 | 0.710 | 0.000 |
| predicted | max_quality | 14978 | 0.989 | 0.0012 | 1.012 | 0.903 | 0.118 | 0.793 | 0.793 | 0.000 |
| predicted | all | 44934 | 0.845 | 0.0062 | 1.002 | 0.860 | 0.191 | 0.699 | 0.709 | 0.001 |
| always_strongest | cheapest_above_threshold | 14978 | 0.260 | 0.0357 | 1.805 | 0.902 | 0.120 | 0.792 | 0.623 | 0.003 |
| always_strongest | max_utility | 14978 | 0.249 | 0.1019 | 1.903 | 0.902 | 0.120 | 0.792 | 0.710 | 0.003 |
| always_strongest | max_quality | 14978 | 0.985 | 0.0044 | 1.013 | 0.902 | 0.120 | 0.792 | 0.793 | 0.003 |
| always_strongest | all | 44934 | 0.498 | 0.0474 | 1.452 | 0.902 | 0.120 | 0.792 | 0.709 | 0.003 |
| always_cheapest | cheapest_above_threshold | 14978 | 0.345 | 0.2248 | 0.055 | 0.555 | 0.608 | 0.348 | 0.623 | 0.046 |
| always_cheapest | max_utility | 14978 | 0.137 | 0.2910 | 0.058 | 0.555 | 0.608 | 0.348 | 0.710 | 0.046 |
| always_cheapest | max_quality | 14978 | 0.013 | 0.1936 | 0.031 | 0.555 | 0.608 | 0.348 | 0.793 | 0.046 |
| always_cheapest | all | 44934 | 0.165 | 0.2365 | 0.045 | 0.555 | 0.608 | 0.348 | 0.709 | 0.046 |
