# Eval: `onnx:artifacts/panda-router-v1` on `gold` (n=329)

Sources: {'swe-rebench': 109, 'swe-smith': 24, 'wildchat': 196}  
Latency (batch 1): p50 5.898 ms, p95 18.545 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.623 / 0.769 / 0.150 |
| difficulty | MAE / Spearman / QWK / ECE | 0.882 / 0.692 / 0.642 / 0.023 |
| skills | mean MAE / mean Spearman / mean ECE | 0.785 / 0.582 / 0.147 |
| flags | F1 macro / AUROC macro / ECE | 0.479 / 0.769 / 0.051 |
| checklist | F1 macro / micro / AUROC | 0.410 / 0.703 / 0.803 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.233 / 0.760 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | -0.019 / 0.004 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 109 | 0.853 | 0.753 | 0.495 | 0.456 | 0.334 |
| swe-smith | 24 | 1.000 | 0.732 | 0.608 | 0.761 | 0.679 |
| wildchat | 196 | 0.449 | 0.972 | 0.608 | 0.181 | 0.288 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 16446 | 0.636 | 0.0079 | 0.784 | 0.852 | 0.197 | 0.566 | 0.575 | 0.000 |
| predicted | max_utility | 16446 | 0.902 | 0.0019 | 0.922 | 0.927 | 0.070 | 0.717 | 0.720 | 0.000 |
| predicted | max_quality | 16446 | 0.988 | 0.0008 | 1.002 | 0.955 | 0.035 | 0.799 | 0.799 | 0.000 |
| predicted | all | 49338 | 0.842 | 0.0035 | 0.957 | 0.911 | 0.101 | 0.694 | 0.698 | 0.000 |
| always_strongest | cheapest_above_threshold | 16446 | 0.155 | -0.0019 | 5.186 | 0.949 | 0.040 | 0.794 | 0.575 | 0.007 |
| always_strongest | max_utility | 16446 | 0.247 | 0.1141 | 3.220 | 0.949 | 0.040 | 0.794 | 0.720 | 0.007 |
| always_strongest | max_quality | 16446 | 0.966 | 0.0090 | 0.999 | 0.949 | 0.040 | 0.794 | 0.799 | 0.007 |
| always_strongest | all | 49338 | 0.456 | 0.0404 | 1.994 | 0.949 | 0.040 | 0.794 | 0.698 | 0.007 |
| always_cheapest | cheapest_above_threshold | 16446 | 0.278 | 0.2377 | 0.042 | 0.606 | 0.569 | 0.325 | 0.575 | 0.016 |
| always_cheapest | max_utility | 16446 | 0.077 | 0.3536 | 0.026 | 0.606 | 0.569 | 0.325 | 0.720 | 0.016 |
| always_cheapest | max_quality | 16446 | 0.012 | 0.2486 | 0.008 | 0.606 | 0.569 | 0.325 | 0.799 | 0.016 |
| always_cheapest | all | 49338 | 0.122 | 0.2800 | 0.016 | 0.606 | 0.569 | 0.325 | 0.698 | 0.016 |
