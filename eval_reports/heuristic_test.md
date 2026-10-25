# Eval: `heuristic` on `test` (n=239)

Sources: {'minimal-pair': 29, 'swe-rebench': 68, 'swe-smith': 31, 'synthetic': 79, 'wildchat': 32}  
Latency (batch 1): p50 1.304 ms, p95 9.833 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.531 / 0.732 / 0.172 |
| difficulty | MAE / Spearman / QWK / ECE | 1.494 / 0.634 / 0.437 / 0.132 |
| skills | mean MAE / mean Spearman / mean ECE | 1.586 / 0.317 / 0.223 |
| flags | F1 macro / AUROC macro / ECE | 0.557 / 0.786 / 0.152 |
| checklist | F1 macro / micro / AUROC | 0.338 / 0.421 / 0.709 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.302 / 0.816 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 29 | 0.655 | 1.791 | 0.830 | 0.643 | 0.333 |
| swe-rebench | 68 | 0.544 | 1.506 | 0.301 | 0.466 | 0.244 |
| swe-smith | 31 | 0.581 | 1.232 | 0.191 | 0.236 | 0.226 |
| synthetic | 79 | 0.392 | 1.686 | 0.531 | 0.519 | 0.317 |
| wildchat | 32 | 0.688 | 0.977 | -0.005 | 0.050 | 0.094 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 11941 | 0.586 | 0.0757 | 0.308 | 0.748 | 0.412 | 0.510 | 0.633 | 0.000 |
| predicted | max_utility | 11941 | 0.776 | 0.0066 | 0.637 | 0.872 | 0.176 | 0.690 | 0.729 | 0.000 |
| predicted | max_quality | 11941 | 0.989 | -0.0006 | 0.989 | 0.933 | 0.069 | 0.818 | 0.819 | 0.000 |
| predicted | all | 35823 | 0.784 | 0.0272 | 0.735 | 0.851 | 0.219 | 0.673 | 0.727 | 0.000 |
| always_strongest | cheapest_above_threshold | 11941 | 0.189 | 0.0383 | 2.056 | 0.933 | 0.069 | 0.818 | 0.633 | 0.002 |
| always_strongest | max_utility | 11941 | 0.198 | 0.1069 | 2.075 | 0.933 | 0.069 | 0.818 | 0.729 | 0.002 |
| always_strongest | max_quality | 11941 | 0.993 | 0.0018 | 1.001 | 0.933 | 0.069 | 0.818 | 0.819 | 0.002 |
| always_strongest | all | 35823 | 0.460 | 0.0490 | 1.525 | 0.933 | 0.069 | 0.818 | 0.727 | 0.002 |
| always_cheapest | cheapest_above_threshold | 11941 | 0.369 | 0.2262 | 0.066 | 0.604 | 0.573 | 0.377 | 0.633 | 0.045 |
| always_cheapest | max_utility | 11941 | 0.149 | 0.2948 | 0.066 | 0.604 | 0.573 | 0.377 | 0.729 | 0.045 |
| always_cheapest | max_quality | 11941 | 0.011 | 0.1897 | 0.032 | 0.604 | 0.573 | 0.377 | 0.819 | 0.045 |
| always_cheapest | all | 35823 | 0.177 | 0.2369 | 0.049 | 0.604 | 0.573 | 0.377 | 0.727 | 0.045 |
