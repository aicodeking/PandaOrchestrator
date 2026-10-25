# Eval: `onnx:artifacts/abl32m_pair0` on `test` (n=300)

Sources: {'minimal-pair': 89, 'swe-rebench': 53, 'swe-smith': 7, 'synthetic': 68, 'wildchat': 83}  
Latency (batch 1): p50 12.412 ms, p95 35.772 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.640 / 0.780 / 0.063 |
| difficulty | MAE / Spearman / QWK / ECE | 0.860 / 0.817 / 0.778 / 0.036 |
| skills | mean MAE / mean Spearman / mean ECE | 1.031 / 0.700 / 0.123 |
| flags | F1 macro / AUROC macro / ECE | 0.747 / 0.897 / 0.042 |
| checklist | F1 macro / micro / AUROC | 0.617 / 0.752 / 0.876 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.225 / 0.727 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 89 | 0.607 | 0.889 | 0.856 | 0.759 | 0.638 |
| swe-rebench | 53 | 0.830 | 0.818 | 0.450 | 0.499 | 0.351 |
| swe-smith | 7 | 1.000 | 0.898 | 0.185 | 0.417 | 0.510 |
| synthetic | 68 | 0.603 | 0.624 | 0.672 | 0.780 | 0.660 |
| wildchat | 83 | 0.554 | 1.047 | 0.642 | 0.254 | 0.273 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 14978 | 0.687 | 0.0002 | 1.010 | 0.831 | 0.235 | 0.625 | 0.623 | 0.002 |
| predicted | max_utility | 14978 | 0.842 | 0.0025 | 0.926 | 0.862 | 0.194 | 0.702 | 0.710 | 0.000 |
| predicted | max_quality | 14978 | 0.989 | 0.0012 | 1.012 | 0.903 | 0.118 | 0.793 | 0.793 | 0.000 |
| predicted | all | 44934 | 0.839 | 0.0013 | 0.990 | 0.865 | 0.182 | 0.707 | 0.709 | 0.001 |
| always_strongest | cheapest_above_threshold | 14978 | 0.260 | 0.0357 | 1.805 | 0.902 | 0.120 | 0.792 | 0.623 | 0.003 |
| always_strongest | max_utility | 14978 | 0.249 | 0.1019 | 1.903 | 0.902 | 0.120 | 0.792 | 0.710 | 0.003 |
| always_strongest | max_quality | 14978 | 0.985 | 0.0044 | 1.013 | 0.902 | 0.120 | 0.792 | 0.793 | 0.003 |
| always_strongest | all | 44934 | 0.498 | 0.0474 | 1.452 | 0.902 | 0.120 | 0.792 | 0.709 | 0.003 |
| always_cheapest | cheapest_above_threshold | 14978 | 0.345 | 0.2248 | 0.055 | 0.555 | 0.608 | 0.348 | 0.623 | 0.046 |
| always_cheapest | max_utility | 14978 | 0.137 | 0.2910 | 0.058 | 0.555 | 0.608 | 0.348 | 0.710 | 0.046 |
| always_cheapest | max_quality | 14978 | 0.013 | 0.1936 | 0.031 | 0.555 | 0.608 | 0.348 | 0.793 | 0.046 |
| always_cheapest | all | 44934 | 0.165 | 0.2365 | 0.045 | 0.555 | 0.608 | 0.348 | 0.709 | 0.046 |
