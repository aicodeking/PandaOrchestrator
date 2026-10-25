# Eval: `onnx:artifacts/s32m_seed0` on `test` (n=300)

Sources: {'minimal-pair': 89, 'swe-rebench': 53, 'swe-smith': 7, 'synthetic': 68, 'wildchat': 83}  
Latency (batch 1): p50 16.871 ms, p95 72.103 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.640 / 0.783 / 0.053 |
| difficulty | MAE / Spearman / QWK / ECE | 0.830 / 0.828 / 0.800 / 0.053 |
| skills | mean MAE / mean Spearman / mean ECE | 1.011 / 0.707 / 0.120 |
| flags | F1 macro / AUROC macro / ECE | 0.757 / 0.896 / 0.048 |
| checklist | F1 macro / micro / AUROC | 0.618 / 0.751 / 0.876 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.220 / 0.720 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 89 | 0.640 | 0.796 | 0.879 | 0.784 | 0.648 |
| swe-rebench | 53 | 0.811 | 0.807 | 0.500 | 0.609 | 0.379 |
| swe-smith | 7 | 1.000 | 0.833 | 0.704 | 0.750 | 0.600 |
| synthetic | 68 | 0.588 | 0.604 | 0.683 | 0.771 | 0.647 |
| wildchat | 83 | 0.542 | 1.065 | 0.607 | 0.213 | 0.269 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 14978 | 0.689 | 0.0009 | 1.037 | 0.834 | 0.227 | 0.628 | 0.623 | 0.001 |
| predicted | max_utility | 14978 | 0.849 | 0.0026 | 0.962 | 0.865 | 0.186 | 0.705 | 0.710 | 0.000 |
| predicted | max_quality | 14978 | 0.990 | 0.0011 | 1.005 | 0.903 | 0.118 | 0.793 | 0.793 | 0.000 |
| predicted | all | 44934 | 0.843 | 0.0015 | 1.003 | 0.868 | 0.177 | 0.709 | 0.709 | 0.000 |
| always_strongest | cheapest_above_threshold | 14978 | 0.260 | 0.0357 | 1.805 | 0.902 | 0.120 | 0.792 | 0.623 | 0.003 |
| always_strongest | max_utility | 14978 | 0.249 | 0.1019 | 1.903 | 0.902 | 0.120 | 0.792 | 0.710 | 0.003 |
| always_strongest | max_quality | 14978 | 0.985 | 0.0044 | 1.013 | 0.902 | 0.120 | 0.792 | 0.793 | 0.003 |
| always_strongest | all | 44934 | 0.498 | 0.0474 | 1.452 | 0.902 | 0.120 | 0.792 | 0.709 | 0.003 |
| always_cheapest | cheapest_above_threshold | 14978 | 0.345 | 0.2248 | 0.055 | 0.555 | 0.608 | 0.348 | 0.623 | 0.046 |
| always_cheapest | max_utility | 14978 | 0.137 | 0.2910 | 0.058 | 0.555 | 0.608 | 0.348 | 0.710 | 0.046 |
| always_cheapest | max_quality | 14978 | 0.013 | 0.1936 | 0.031 | 0.555 | 0.608 | 0.348 | 0.793 | 0.046 |
| always_cheapest | all | 44934 | 0.165 | 0.2365 | 0.045 | 0.555 | 0.608 | 0.348 | 0.709 | 0.046 |
