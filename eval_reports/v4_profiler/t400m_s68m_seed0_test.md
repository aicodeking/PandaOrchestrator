# Eval: `onnx:artifacts/v4_candidates/t400m_s68m_seed0` on `test` (n=603)

Sources: {'minimal-pair': 64, 'swe-rebench': 120, 'synthetic': 320, 'wildchat': 99}  
Latency (batch 1): p50 16.486 ms, p95 80.25 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.819 / 0.939 / 0.092 |
| difficulty | MAE / Spearman / QWK / ECE | 0.739 / 0.881 / 0.841 / 0.057 |
| skills | mean MAE / mean Spearman / mean ECE | 0.797 / 0.824 / 0.080 |
| flags | F1 macro / AUROC macro / ECE | 0.819 / 0.929 / 0.032 |
| checklist | F1 macro / micro / AUROC | 0.732 / 0.817 / 0.915 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.169 / 0.803 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 64 | 0.797 | 0.673 | 0.820 | 0.755 | 0.689 |
| swe-rebench | 120 | 0.892 | 0.728 | 0.512 | 0.637 | 0.389 |
| synthetic | 320 | 0.781 | 0.690 | 0.834 | 0.874 | 0.757 |
| wildchat | 99 | 0.869 | 0.952 | 0.616 | 0.237 | 0.416 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 30097 | 0.716 | -0.0116 | 1.065 | 0.771 | 0.348 | 0.582 | 0.558 | 0.000 |
| predicted | max_utility | 30097 | 0.867 | 0.0012 | 0.935 | 0.778 | 0.353 | 0.616 | 0.621 | 0.000 |
| predicted | max_quality | 30097 | 0.988 | 0.0005 | 1.005 | 0.813 | 0.285 | 0.682 | 0.682 | 0.000 |
| predicted | all | 90291 | 0.857 | -0.0033 | 1.005 | 0.787 | 0.329 | 0.627 | 0.621 | 0.000 |
| always_strongest | cheapest_above_threshold | 30097 | 0.454 | 0.0199 | 1.415 | 0.806 | 0.291 | 0.677 | 0.558 | 0.012 |
| always_strongest | max_utility | 30097 | 0.442 | 0.0859 | 1.662 | 0.806 | 0.291 | 0.677 | 0.621 | 0.012 |
| always_strongest | max_quality | 30097 | 0.966 | 0.0140 | 1.001 | 0.806 | 0.291 | 0.677 | 0.682 | 0.012 |
| always_strongest | all | 90291 | 0.621 | 0.0399 | 1.300 | 0.806 | 0.291 | 0.677 | 0.621 | 0.012 |
| always_cheapest | cheapest_above_threshold | 30097 | 0.138 | 0.3526 | 0.012 | 0.351 | 0.802 | 0.192 | 0.558 | 0.102 |
| always_cheapest | max_utility | 30097 | 0.053 | 0.4187 | 0.015 | 0.351 | 0.802 | 0.192 | 0.621 | 0.102 |
| always_cheapest | max_quality | 30097 | 0.013 | 0.3467 | 0.009 | 0.351 | 0.802 | 0.192 | 0.682 | 0.102 |
| always_cheapest | all | 90291 | 0.068 | 0.3726 | 0.011 | 0.351 | 0.802 | 0.192 | 0.621 | 0.102 |
