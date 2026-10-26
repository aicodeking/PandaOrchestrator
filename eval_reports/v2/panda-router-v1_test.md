# Eval: `onnx:artifacts/panda-router-v1` on `test` (n=364)

Sources: {'minimal-pair': 78, 'swe-rebench': 53, 'swe-smith': 20, 'synthetic': 148, 'wildchat': 65}  
Latency (batch 1): p50 10.39 ms, p95 48.984 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.775 / 0.863 / 0.054 |
| difficulty | MAE / Spearman / QWK / ECE | 0.686 / 0.912 / 0.853 / 0.039 |
| skills | mean MAE / mean Spearman / mean ECE | 0.950 / 0.775 / 0.113 |
| flags | F1 macro / AUROC macro / ECE | 0.813 / 0.953 / 0.041 |
| checklist | F1 macro / micro / AUROC | 0.634 / 0.793 / 0.908 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.173 / 0.863 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 78 | 0.756 | 0.540 | 0.940 | 0.827 | 0.670 |
| swe-rebench | 53 | 0.887 | 0.525 | 0.807 | 0.642 | 0.408 |
| swe-smith | 20 | 1.000 | 0.537 | 0.658 | 0.393 | 0.486 |
| synthetic | 148 | 0.696 | 0.875 | 0.806 | 0.850 | 0.624 |
| wildchat | 65 | 0.815 | 0.607 | 0.882 | 0.395 | 0.410 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 18170 | 0.757 | -0.0047 | 0.970 | 0.770 | 0.315 | 0.553 | 0.550 | 0.000 |
| predicted | max_utility | 18170 | 0.876 | -0.0039 | 0.807 | 0.792 | 0.296 | 0.621 | 0.632 | 0.000 |
| predicted | max_quality | 18170 | 0.989 | 0.0003 | 1.006 | 0.830 | 0.236 | 0.696 | 0.696 | 0.000 |
| predicted | all | 54510 | 0.874 | -0.0027 | 0.943 | 0.797 | 0.282 | 0.623 | 0.626 | 0.000 |
| always_strongest | cheapest_above_threshold | 18170 | 0.388 | 0.0187 | 1.628 | 0.821 | 0.243 | 0.690 | 0.550 | 0.014 |
| always_strongest | max_utility | 18170 | 0.401 | 0.0939 | 1.743 | 0.821 | 0.243 | 0.690 | 0.632 | 0.014 |
| always_strongest | max_quality | 18170 | 0.964 | 0.0157 | 1.006 | 0.821 | 0.243 | 0.690 | 0.696 | 0.014 |
| always_strongest | all | 54510 | 0.584 | 0.0428 | 1.375 | 0.821 | 0.243 | 0.690 | 0.626 | 0.014 |
| always_cheapest | cheapest_above_threshold | 18170 | 0.165 | 0.3111 | 0.015 | 0.400 | 0.760 | 0.218 | 0.550 | 0.082 |
| always_cheapest | max_utility | 18170 | 0.059 | 0.3863 | 0.016 | 0.400 | 0.760 | 0.218 | 0.632 | 0.082 |
| always_cheapest | max_quality | 18170 | 0.014 | 0.3081 | 0.009 | 0.400 | 0.760 | 0.218 | 0.696 | 0.082 |
| always_cheapest | all | 54510 | 0.079 | 0.3352 | 0.012 | 0.400 | 0.760 | 0.218 | 0.626 | 0.082 |
