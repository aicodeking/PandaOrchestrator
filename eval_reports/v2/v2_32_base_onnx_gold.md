# Eval: `onnx:artifacts/v2_32_base_onnx` on `gold` (n=329)

Sources: {'swe-rebench': 109, 'swe-smith': 24, 'wildchat': 196}  
Latency (batch 1): p50 12.952 ms, p95 55.698 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.660 / 0.796 / 0.101 |
| difficulty | MAE / Spearman / QWK / ECE | 0.877 / 0.715 / 0.638 / 0.033 |
| skills | mean MAE / mean Spearman / mean ECE | 0.750 / 0.607 / 0.149 |
| flags | F1 macro / AUROC macro / ECE | 0.469 / 0.813 / 0.054 |
| checklist | F1 macro / micro / AUROC | 0.482 / 0.713 / 0.849 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.234 / 0.687 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | -0.017 / 0.004 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 109 | 0.862 | 0.779 | 0.543 | 0.449 | 0.336 |
| swe-smith | 24 | 1.000 | 0.660 | 0.742 | 0.625 | 0.612 |
| wildchat | 196 | 0.505 | 0.958 | 0.640 | 0.217 | 0.385 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 16446 | 0.648 | 0.0268 | 0.739 | 0.835 | 0.232 | 0.543 | 0.575 | 0.000 |
| predicted | max_utility | 16446 | 0.905 | 0.0020 | 0.899 | 0.925 | 0.072 | 0.714 | 0.720 | 0.000 |
| predicted | max_quality | 16446 | 0.989 | 0.0005 | 1.001 | 0.955 | 0.035 | 0.799 | 0.799 | 0.000 |
| predicted | all | 49338 | 0.847 | 0.0098 | 0.946 | 0.905 | 0.113 | 0.685 | 0.698 | 0.000 |
| always_strongest | cheapest_above_threshold | 16446 | 0.155 | -0.0019 | 5.186 | 0.949 | 0.040 | 0.794 | 0.575 | 0.007 |
| always_strongest | max_utility | 16446 | 0.247 | 0.1141 | 3.220 | 0.949 | 0.040 | 0.794 | 0.720 | 0.007 |
| always_strongest | max_quality | 16446 | 0.966 | 0.0090 | 0.999 | 0.949 | 0.040 | 0.794 | 0.799 | 0.007 |
| always_strongest | all | 49338 | 0.456 | 0.0404 | 1.994 | 0.949 | 0.040 | 0.794 | 0.698 | 0.007 |
| always_cheapest | cheapest_above_threshold | 16446 | 0.278 | 0.2377 | 0.042 | 0.606 | 0.569 | 0.325 | 0.575 | 0.016 |
| always_cheapest | max_utility | 16446 | 0.077 | 0.3536 | 0.026 | 0.606 | 0.569 | 0.325 | 0.720 | 0.016 |
| always_cheapest | max_quality | 16446 | 0.012 | 0.2486 | 0.008 | 0.606 | 0.569 | 0.325 | 0.799 | 0.016 |
| always_cheapest | all | 49338 | 0.122 | 0.2800 | 0.016 | 0.606 | 0.569 | 0.325 | 0.698 | 0.016 |
