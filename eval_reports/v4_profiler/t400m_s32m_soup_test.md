# Eval: `onnx:artifacts/v4_candidates/t400m_s32m_soup` on `test` (n=603)

Sources: {'minimal-pair': 64, 'swe-rebench': 120, 'synthetic': 320, 'wildchat': 99}  
Latency (batch 1): p50 4.78 ms, p95 18.247 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.781 / 0.920 / 0.073 |
| difficulty | MAE / Spearman / QWK / ECE | 0.729 / 0.893 / 0.844 / 0.070 |
| skills | mean MAE / mean Spearman / mean ECE | 0.788 / 0.826 / 0.088 |
| flags | F1 macro / AUROC macro / ECE | 0.838 / 0.928 / 0.028 |
| checklist | F1 macro / micro / AUROC | 0.744 / 0.822 / 0.917 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.155 / 0.831 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 64 | 0.734 | 0.721 | 0.827 | 0.758 | 0.702 |
| swe-rebench | 120 | 0.917 | 0.673 | 0.621 | 0.685 | 0.454 |
| synthetic | 320 | 0.728 | 0.669 | 0.850 | 0.893 | 0.758 |
| wildchat | 99 | 0.818 | 0.995 | 0.513 | 0.197 | 0.372 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 30097 | 0.720 | -0.0077 | 1.062 | 0.764 | 0.365 | 0.573 | 0.558 | 0.000 |
| predicted | max_utility | 30097 | 0.869 | 0.0004 | 0.927 | 0.777 | 0.356 | 0.614 | 0.621 | 0.000 |
| predicted | max_quality | 30097 | 0.988 | 0.0005 | 1.005 | 0.813 | 0.285 | 0.682 | 0.682 | 0.000 |
| predicted | all | 90291 | 0.859 | -0.0023 | 1.002 | 0.785 | 0.335 | 0.623 | 0.621 | 0.000 |
| always_strongest | cheapest_above_threshold | 30097 | 0.454 | 0.0199 | 1.415 | 0.806 | 0.291 | 0.677 | 0.558 | 0.012 |
| always_strongest | max_utility | 30097 | 0.442 | 0.0859 | 1.662 | 0.806 | 0.291 | 0.677 | 0.621 | 0.012 |
| always_strongest | max_quality | 30097 | 0.966 | 0.0140 | 1.001 | 0.806 | 0.291 | 0.677 | 0.682 | 0.012 |
| always_strongest | all | 90291 | 0.621 | 0.0399 | 1.300 | 0.806 | 0.291 | 0.677 | 0.621 | 0.012 |
| always_cheapest | cheapest_above_threshold | 30097 | 0.138 | 0.3526 | 0.012 | 0.351 | 0.802 | 0.192 | 0.558 | 0.102 |
| always_cheapest | max_utility | 30097 | 0.053 | 0.4187 | 0.015 | 0.351 | 0.802 | 0.192 | 0.621 | 0.102 |
| always_cheapest | max_quality | 30097 | 0.013 | 0.3467 | 0.009 | 0.351 | 0.802 | 0.192 | 0.682 | 0.102 |
| always_cheapest | all | 90291 | 0.068 | 0.3726 | 0.011 | 0.351 | 0.802 | 0.192 | 0.621 | 0.102 |
