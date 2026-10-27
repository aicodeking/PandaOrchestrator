# Eval: `onnx:artifacts/v4_candidates/t150m_s68m_seed0` on `test` (n=603)

Sources: {'minimal-pair': 64, 'swe-rebench': 120, 'synthetic': 320, 'wildchat': 99}  
Latency (batch 1): p50 10.54 ms, p95 41.239 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.804 / 0.934 / 0.087 |
| difficulty | MAE / Spearman / QWK / ECE | 0.738 / 0.877 / 0.836 / 0.052 |
| skills | mean MAE / mean Spearman / mean ECE | 0.763 / 0.831 / 0.089 |
| flags | F1 macro / AUROC macro / ECE | 0.836 / 0.930 / 0.027 |
| checklist | F1 macro / micro / AUROC | 0.755 / 0.827 / 0.922 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.167 / 0.834 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 64 | 0.797 | 0.692 | 0.820 | 0.808 | 0.716 |
| swe-rebench | 120 | 0.900 | 0.724 | 0.506 | 0.662 | 0.404 |
| synthetic | 320 | 0.753 | 0.679 | 0.831 | 0.888 | 0.780 |
| wildchat | 99 | 0.859 | 0.976 | 0.605 | 0.290 | 0.421 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 30097 | 0.716 | -0.0077 | 1.068 | 0.767 | 0.358 | 0.577 | 0.558 | 0.000 |
| predicted | max_utility | 30097 | 0.869 | 0.0010 | 0.936 | 0.777 | 0.353 | 0.616 | 0.621 | 0.000 |
| predicted | max_quality | 30097 | 0.989 | 0.0005 | 1.005 | 0.813 | 0.285 | 0.682 | 0.682 | 0.000 |
| predicted | all | 90291 | 0.858 | -0.0021 | 1.006 | 0.786 | 0.332 | 0.625 | 0.621 | 0.000 |
| always_strongest | cheapest_above_threshold | 30097 | 0.454 | 0.0199 | 1.415 | 0.806 | 0.291 | 0.677 | 0.558 | 0.012 |
| always_strongest | max_utility | 30097 | 0.442 | 0.0859 | 1.662 | 0.806 | 0.291 | 0.677 | 0.621 | 0.012 |
| always_strongest | max_quality | 30097 | 0.966 | 0.0140 | 1.001 | 0.806 | 0.291 | 0.677 | 0.682 | 0.012 |
| always_strongest | all | 90291 | 0.621 | 0.0399 | 1.300 | 0.806 | 0.291 | 0.677 | 0.621 | 0.012 |
| always_cheapest | cheapest_above_threshold | 30097 | 0.138 | 0.3526 | 0.012 | 0.351 | 0.802 | 0.192 | 0.558 | 0.102 |
| always_cheapest | max_utility | 30097 | 0.053 | 0.4187 | 0.015 | 0.351 | 0.802 | 0.192 | 0.621 | 0.102 |
| always_cheapest | max_quality | 30097 | 0.013 | 0.3467 | 0.009 | 0.351 | 0.802 | 0.192 | 0.682 | 0.102 |
| always_cheapest | all | 90291 | 0.068 | 0.3726 | 0.011 | 0.351 | 0.802 | 0.192 | 0.621 | 0.102 |
