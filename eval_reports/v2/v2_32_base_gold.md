# Eval: `torch:checkpoints/v2_32_base/best` on `gold` (n=329)

Sources: {'swe-rebench': 109, 'swe-smith': 24, 'wildchat': 196}  
Latency (batch 1): p50 165.855 ms, p95 814.673 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.656 / 0.796 / 0.102 |
| difficulty | MAE / Spearman / QWK / ECE | 0.878 / 0.714 / 0.625 / 0.031 |
| skills | mean MAE / mean Spearman / mean ECE | 0.746 / 0.607 / 0.144 |
| flags | F1 macro / AUROC macro / ECE | 0.470 / 0.814 / 0.052 |
| checklist | F1 macro / micro / AUROC | 0.476 / 0.712 / 0.851 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.236 / 0.687 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | -0.035 / 0.004 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 109 | 0.872 | 0.778 | 0.543 | 0.441 | 0.337 |
| swe-smith | 24 | 1.000 | 0.652 | 0.741 | 0.625 | 0.668 |
| wildchat | 196 | 0.495 | 0.961 | 0.635 | 0.214 | 0.372 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 16446 | 0.647 | 0.0238 | 0.739 | 0.837 | 0.227 | 0.546 | 0.575 | 0.000 |
| predicted | max_utility | 16446 | 0.905 | 0.0019 | 0.898 | 0.926 | 0.071 | 0.715 | 0.720 | 0.000 |
| predicted | max_quality | 16446 | 0.989 | 0.0005 | 1.001 | 0.955 | 0.035 | 0.799 | 0.799 | 0.000 |
| predicted | all | 49338 | 0.847 | 0.0088 | 0.946 | 0.906 | 0.111 | 0.687 | 0.698 | 0.000 |
| always_strongest | cheapest_above_threshold | 16446 | 0.155 | -0.0019 | 5.186 | 0.949 | 0.040 | 0.794 | 0.575 | 0.007 |
| always_strongest | max_utility | 16446 | 0.247 | 0.1141 | 3.220 | 0.949 | 0.040 | 0.794 | 0.720 | 0.007 |
| always_strongest | max_quality | 16446 | 0.966 | 0.0090 | 0.999 | 0.949 | 0.040 | 0.794 | 0.799 | 0.007 |
| always_strongest | all | 49338 | 0.456 | 0.0404 | 1.994 | 0.949 | 0.040 | 0.794 | 0.698 | 0.007 |
| always_cheapest | cheapest_above_threshold | 16446 | 0.278 | 0.2377 | 0.042 | 0.606 | 0.569 | 0.325 | 0.575 | 0.016 |
| always_cheapest | max_utility | 16446 | 0.077 | 0.3536 | 0.026 | 0.606 | 0.569 | 0.325 | 0.720 | 0.016 |
| always_cheapest | max_quality | 16446 | 0.012 | 0.2486 | 0.008 | 0.606 | 0.569 | 0.325 | 0.799 | 0.016 |
| always_cheapest | all | 49338 | 0.122 | 0.2800 | 0.016 | 0.606 | 0.569 | 0.325 | 0.698 | 0.016 |
