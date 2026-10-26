# Eval: `onnx:artifacts/abl32m_anchor` on `test` (n=300)

Sources: {'minimal-pair': 89, 'swe-rebench': 53, 'swe-smith': 7, 'synthetic': 68, 'wildchat': 83}  
Latency (batch 1): p50 127.387 ms, p95 1504.887 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.640 / 0.790 / 0.057 |
| difficulty | MAE / Spearman / QWK / ECE | 0.890 / 0.816 / 0.778 / 0.053 |
| skills | mean MAE / mean Spearman / mean ECE | 1.041 / 0.698 / 0.125 |
| flags | F1 macro / AUROC macro / ECE | 0.754 / 0.892 / 0.053 |
| checklist | F1 macro / micro / AUROC | 0.612 / 0.751 / 0.872 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.223 / 0.693 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 89 | 0.629 | 0.839 | 0.863 | 0.775 | 0.637 |
| swe-rebench | 53 | 0.830 | 0.979 | 0.419 | 0.556 | 0.392 |
| swe-smith | 7 | 1.000 | 1.030 | 0.778 | 0.750 | 0.600 |
| synthetic | 68 | 0.544 | 0.634 | 0.652 | 0.782 | 0.635 |
| wildchat | 83 | 0.578 | 1.085 | 0.597 | 0.233 | 0.274 |

## Routing (cards: cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 14978 | 0.663 | -0.0047 | 1.089 | 0.843 | 0.213 | 0.640 | 0.623 | 0.000 |
| predicted | max_utility | 14978 | 0.841 | 0.0029 | 0.954 | 0.866 | 0.184 | 0.708 | 0.710 | 0.000 |
| predicted | max_quality | 14978 | 0.989 | 0.0012 | 1.012 | 0.903 | 0.118 | 0.793 | 0.793 | 0.000 |
| predicted | all | 44934 | 0.831 | -0.0002 | 1.018 | 0.871 | 0.172 | 0.714 | 0.709 | 0.000 |
| always_strongest | cheapest_above_threshold | 14978 | 0.260 | 0.0357 | 1.805 | 0.902 | 0.120 | 0.792 | 0.623 | 0.003 |
| always_strongest | max_utility | 14978 | 0.249 | 0.1019 | 1.903 | 0.902 | 0.120 | 0.792 | 0.710 | 0.003 |
| always_strongest | max_quality | 14978 | 0.985 | 0.0044 | 1.013 | 0.902 | 0.120 | 0.792 | 0.793 | 0.003 |
| always_strongest | all | 44934 | 0.498 | 0.0474 | 1.452 | 0.902 | 0.120 | 0.792 | 0.709 | 0.003 |
| always_cheapest | cheapest_above_threshold | 14978 | 0.345 | 0.2248 | 0.055 | 0.555 | 0.608 | 0.348 | 0.623 | 0.046 |
| always_cheapest | max_utility | 14978 | 0.137 | 0.2910 | 0.058 | 0.555 | 0.608 | 0.348 | 0.710 | 0.046 |
| always_cheapest | max_quality | 14978 | 0.013 | 0.1936 | 0.031 | 0.555 | 0.608 | 0.348 | 0.793 | 0.046 |
| always_cheapest | all | 44934 | 0.165 | 0.2365 | 0.045 | 0.555 | 0.608 | 0.348 | 0.709 | 0.046 |
