# Eval: `onnx:/tmp/v4ft` on `test` (n=603)

Sources: {'minimal-pair': 64, 'swe-rebench': 120, 'synthetic': 320, 'wildchat': 99}  
Latency (batch 1): p50 13.76 ms, p95 74.589 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.793 / 0.930 / 0.077 |
| difficulty | MAE / Spearman / QWK / ECE | 0.745 / 0.884 / 0.842 / 0.036 |
| skills | mean MAE / mean Spearman / mean ECE | 0.771 / 0.828 / 0.094 |
| flags | F1 macro / AUROC macro / ECE | 0.837 / 0.927 / 0.026 |
| checklist | F1 macro / micro / AUROC | 0.761 / 0.828 / 0.920 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.155 / 0.798 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 64 | 0.766 | 0.730 | 0.825 | 0.772 | 0.717 |
| swe-rebench | 120 | 0.917 | 0.783 | 0.461 | 0.657 | 0.437 |
| synthetic | 320 | 0.744 | 0.679 | 0.847 | 0.895 | 0.789 |
| wildchat | 99 | 0.818 | 0.920 | 0.600 | 0.251 | 0.403 |

## Routing (cards: /Users/king/PandaOrchestrator/cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 30097 | 0.713 | -0.0052 | 1.049 | 0.763 | 0.371 | 0.571 | 0.558 | 0.000 |
| predicted | max_utility | 30097 | 0.869 | 0.0002 | 0.917 | 0.776 | 0.357 | 0.614 | 0.621 | 0.000 |
| predicted | max_quality | 30097 | 0.988 | 0.0004 | 1.006 | 0.813 | 0.285 | 0.682 | 0.682 | 0.000 |
| predicted | all | 90291 | 0.857 | -0.0015 | 0.996 | 0.784 | 0.338 | 0.622 | 0.621 | 0.000 |
| always_strongest | cheapest_above_threshold | 30097 | 0.454 | 0.0199 | 1.415 | 0.806 | 0.291 | 0.677 | 0.558 | 0.012 |
| always_strongest | max_utility | 30097 | 0.442 | 0.0859 | 1.662 | 0.806 | 0.291 | 0.677 | 0.621 | 0.012 |
| always_strongest | max_quality | 30097 | 0.966 | 0.0140 | 1.001 | 0.806 | 0.291 | 0.677 | 0.682 | 0.012 |
| always_strongest | all | 90291 | 0.621 | 0.0399 | 1.300 | 0.806 | 0.291 | 0.677 | 0.621 | 0.012 |
| always_cheapest | cheapest_above_threshold | 30097 | 0.138 | 0.3526 | 0.012 | 0.351 | 0.802 | 0.192 | 0.558 | 0.102 |
| always_cheapest | max_utility | 30097 | 0.053 | 0.4187 | 0.015 | 0.351 | 0.802 | 0.192 | 0.621 | 0.102 |
| always_cheapest | max_quality | 30097 | 0.013 | 0.3467 | 0.009 | 0.351 | 0.802 | 0.192 | 0.682 | 0.102 |
| always_cheapest | all | 90291 | 0.068 | 0.3726 | 0.011 | 0.351 | 0.802 | 0.192 | 0.621 | 0.102 |
