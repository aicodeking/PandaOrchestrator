# Eval: `onnx:artifacts/abl32m_regret0` on `test` (n=300)

Sources: {'minimal-pair': 89, 'swe-rebench': 53, 'swe-smith': 7, 'synthetic': 68, 'wildchat': 83}  
Latency (batch 1): p50 13.492 ms, p95 37.087 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.677 / 0.793 / 0.066 |
| difficulty | MAE / Spearman / QWK / ECE | 0.854 / 0.822 / 0.788 / 0.020 |
| skills | mean MAE / mean Spearman / mean ECE | 1.012 / 0.705 / 0.118 |
| flags | F1 macro / AUROC macro / ECE | 0.746 / 0.893 / 0.040 |
| checklist | F1 macro / micro / AUROC | 0.608 / 0.745 / 0.877 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.221 / 0.753 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 89 | 0.652 | 0.837 | 0.878 | 0.775 | 0.641 |
| swe-rebench | 53 | 0.830 | 0.826 | 0.444 | 0.451 | 0.330 |
| swe-smith | 7 | 1.000 | 0.914 | 0.630 | 0.250 | 0.510 |
| synthetic | 68 | 0.647 | 0.626 | 0.651 | 0.756 | 0.641 |
| wildchat | 83 | 0.602 | 1.074 | 0.626 | 0.251 | 0.270 |

## Routing (cards: cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 14978 | 0.712 | 0.0029 | 0.977 | 0.824 | 0.247 | 0.614 | 0.623 | 0.001 |
| predicted | max_utility | 14978 | 0.843 | 0.0025 | 0.934 | 0.861 | 0.196 | 0.701 | 0.710 | 0.000 |
| predicted | max_quality | 14978 | 0.989 | 0.0011 | 1.010 | 0.903 | 0.118 | 0.793 | 0.793 | 0.000 |
| predicted | all | 44934 | 0.848 | 0.0022 | 0.982 | 0.863 | 0.187 | 0.703 | 0.709 | 0.000 |
| always_strongest | cheapest_above_threshold | 14978 | 0.260 | 0.0357 | 1.805 | 0.902 | 0.120 | 0.792 | 0.623 | 0.003 |
| always_strongest | max_utility | 14978 | 0.249 | 0.1019 | 1.903 | 0.902 | 0.120 | 0.792 | 0.710 | 0.003 |
| always_strongest | max_quality | 14978 | 0.985 | 0.0044 | 1.013 | 0.902 | 0.120 | 0.792 | 0.793 | 0.003 |
| always_strongest | all | 44934 | 0.498 | 0.0474 | 1.452 | 0.902 | 0.120 | 0.792 | 0.709 | 0.003 |
| always_cheapest | cheapest_above_threshold | 14978 | 0.345 | 0.2248 | 0.055 | 0.555 | 0.608 | 0.348 | 0.623 | 0.046 |
| always_cheapest | max_utility | 14978 | 0.137 | 0.2910 | 0.058 | 0.555 | 0.608 | 0.348 | 0.710 | 0.046 |
| always_cheapest | max_quality | 14978 | 0.013 | 0.1936 | 0.031 | 0.555 | 0.608 | 0.348 | 0.793 | 0.046 |
| always_cheapest | all | 44934 | 0.165 | 0.2365 | 0.045 | 0.555 | 0.608 | 0.348 | 0.709 | 0.046 |
