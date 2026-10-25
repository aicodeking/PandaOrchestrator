# Eval: `onnx:artifacts/s68m_soup` on `test` (n=300)

Sources: {'minimal-pair': 89, 'swe-rebench': 53, 'swe-smith': 7, 'synthetic': 68, 'wildchat': 83}  
Latency (batch 1): p50 56.82 ms, p95 217.945 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.693 / 0.823 / 0.055 |
| difficulty | MAE / Spearman / QWK / ECE | 0.858 / 0.828 / 0.786 / 0.019 |
| skills | mean MAE / mean Spearman / mean ECE | 1.001 / 0.710 / 0.111 |
| flags | F1 macro / AUROC macro / ECE | 0.746 / 0.899 / 0.044 |
| checklist | F1 macro / micro / AUROC | 0.604 / 0.748 / 0.875 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.215 / 0.733 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 89 | 0.708 | 0.886 | 0.866 | 0.759 | 0.624 |
| swe-rebench | 53 | 0.792 | 0.810 | 0.487 | 0.588 | 0.383 |
| swe-smith | 7 | 1.000 | 0.789 | 0.741 | 0.750 | 0.494 |
| synthetic | 68 | 0.735 | 0.662 | 0.641 | 0.772 | 0.635 |
| wildchat | 83 | 0.554 | 1.025 | 0.664 | 0.252 | 0.278 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 14978 | 0.697 | 0.0029 | 1.014 | 0.828 | 0.236 | 0.620 | 0.623 | 0.002 |
| predicted | max_utility | 14978 | 0.850 | 0.0028 | 0.954 | 0.863 | 0.189 | 0.703 | 0.710 | 0.000 |
| predicted | max_quality | 14978 | 0.990 | 0.0010 | 1.003 | 0.903 | 0.118 | 0.793 | 0.793 | 0.000 |
| predicted | all | 44934 | 0.846 | 0.0022 | 0.993 | 0.865 | 0.181 | 0.705 | 0.709 | 0.001 |
| always_strongest | cheapest_above_threshold | 14978 | 0.260 | 0.0357 | 1.805 | 0.902 | 0.120 | 0.792 | 0.623 | 0.003 |
| always_strongest | max_utility | 14978 | 0.249 | 0.1019 | 1.903 | 0.902 | 0.120 | 0.792 | 0.710 | 0.003 |
| always_strongest | max_quality | 14978 | 0.985 | 0.0044 | 1.013 | 0.902 | 0.120 | 0.792 | 0.793 | 0.003 |
| always_strongest | all | 44934 | 0.498 | 0.0474 | 1.452 | 0.902 | 0.120 | 0.792 | 0.709 | 0.003 |
| always_cheapest | cheapest_above_threshold | 14978 | 0.345 | 0.2248 | 0.055 | 0.555 | 0.608 | 0.348 | 0.623 | 0.046 |
| always_cheapest | max_utility | 14978 | 0.137 | 0.2910 | 0.058 | 0.555 | 0.608 | 0.348 | 0.710 | 0.046 |
| always_cheapest | max_quality | 14978 | 0.013 | 0.1936 | 0.031 | 0.555 | 0.608 | 0.348 | 0.793 | 0.046 |
| always_cheapest | all | 44934 | 0.165 | 0.2365 | 0.045 | 0.555 | 0.608 | 0.348 | 0.709 | 0.046 |
