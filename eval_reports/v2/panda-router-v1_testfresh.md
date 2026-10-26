# Eval: `onnx:artifacts/panda-router-v1` on `test` (n=120)

Sources: {'minimal-pair': 15, 'swe-rebench': 11, 'synthetic': 83, 'wildchat': 11}  
Latency (batch 1): p50 15.631 ms, p95 59.145 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.642 / 0.758 / 0.095 |
| difficulty | MAE / Spearman / QWK / ECE | 1.075 / 0.808 / 0.699 / 0.101 |
| skills | mean MAE / mean Spearman / mean ECE | 1.456 / 0.721 / 0.113 |
| flags | F1 macro / AUROC macro / ECE | 0.816 / 0.921 / 0.062 |
| checklist | F1 macro / micro / AUROC | 0.599 / 0.762 / 0.857 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.281 / 0.658 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 15 | 0.533 | 0.633 | 0.928 | 0.821 | 0.630 |
| swe-rebench | 11 | 0.909 | 0.570 | 0.727 | 0.650 | 0.330 |
| synthetic | 83 | 0.626 | 1.235 | 0.697 | 0.825 | 0.591 |
| wildchat | 11 | 0.636 | 0.977 | 0.618 | 0.367 | 0.332 |

## Routing (cards: cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 5994 | 0.720 | -0.0073 | 0.938 | 0.658 | 0.488 | 0.499 | 0.495 | 0.000 |
| predicted | max_utility | 5994 | 0.778 | -0.0106 | 0.695 | 0.656 | 0.487 | 0.520 | 0.545 | 0.000 |
| predicted | max_quality | 5994 | 0.982 | 0.0005 | 1.012 | 0.705 | 0.424 | 0.592 | 0.592 | 0.000 |
| predicted | all | 17982 | 0.827 | -0.0058 | 0.898 | 0.673 | 0.466 | 0.537 | 0.544 | 0.000 |
| always_strongest | cheapest_above_threshold | 5994 | 0.555 | 0.0233 | 1.393 | 0.698 | 0.428 | 0.587 | 0.495 | 0.013 |
| always_strongest | max_utility | 5994 | 0.552 | 0.0716 | 1.442 | 0.698 | 0.428 | 0.587 | 0.545 | 0.013 |
| always_strongest | max_quality | 5994 | 0.962 | 0.0153 | 1.012 | 0.698 | 0.428 | 0.587 | 0.592 | 0.013 |
| always_strongest | all | 17982 | 0.690 | 0.0367 | 1.250 | 0.698 | 0.428 | 0.587 | 0.544 | 0.013 |
| always_cheapest | cheapest_above_threshold | 5994 | 0.096 | 0.2779 | 0.013 | 0.266 | 0.870 | 0.145 | 0.495 | 0.071 |
| always_cheapest | max_utility | 5994 | 0.042 | 0.3262 | 0.013 | 0.266 | 0.870 | 0.145 | 0.545 | 0.071 |
| always_cheapest | max_quality | 5994 | 0.014 | 0.2699 | 0.009 | 0.266 | 0.870 | 0.145 | 0.592 | 0.071 |
| always_cheapest | all | 17982 | 0.051 | 0.2913 | 0.011 | 0.266 | 0.870 | 0.145 | 0.544 | 0.071 |
