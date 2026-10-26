# Eval: `onnx:artifacts/s32m_seed0` on `gold` (n=285)

Sources: {'swe-rebench': 92, 'swe-smith': 23, 'wildchat': 170}  
Latency (batch 1): p50 12.571 ms, p95 55.039 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.600 / 0.782 / 0.152 |
| difficulty | MAE / Spearman / QWK / ECE | 0.876 / 0.712 / 0.655 / 0.009 |
| skills | mean MAE / mean Spearman / mean ECE | 0.797 / 0.599 / 0.158 |
| flags | F1 macro / AUROC macro / ECE | 0.518 / 0.817 / 0.047 |
| checklist | F1 macro / micro / AUROC | 0.397 / 0.690 / 0.820 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.233 / 0.681 |
| difficulty vs IRT anchors | Spearman pred / label (n=92) | 0.143 / 0.004 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| swe-rebench | 92 | 0.804 | 0.694 | 0.592 | 0.523 | 0.336 |
| swe-smith | 23 | 1.000 | 0.623 | 0.609 | 0.799 | 0.740 |
| wildchat | 170 | 0.435 | 1.009 | 0.601 | 0.209 | 0.261 |

## Routing (cards: cards, 500 pools, 50 pools/task)

| policy | mode | n | pick agree | utility regret | cost ratio | P(success) | P<0.75 | P·quality | oracle P·quality | infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | cheapest_above_threshold | 14248 | 0.753 | 0.0066 | 0.699 | 0.881 | 0.132 | 0.611 | 0.622 | 0.000 |
| predicted | max_utility | 14248 | 0.876 | 0.0028 | 0.929 | 0.944 | 0.042 | 0.755 | 0.757 | 0.000 |
| predicted | max_quality | 14248 | 0.983 | 0.0023 | 1.007 | 0.974 | 0.012 | 0.853 | 0.853 | 0.000 |
| predicted | all | 42744 | 0.871 | 0.0039 | 0.957 | 0.933 | 0.062 | 0.740 | 0.744 | 0.000 |
| always_strongest | cheapest_above_threshold | 14248 | 0.074 | 0.0310 | 6.393 | 0.974 | 0.012 | 0.853 | 0.622 | 0.000 |
| always_strongest | max_utility | 14248 | 0.124 | 0.1220 | 3.058 | 0.974 | 0.012 | 0.853 | 0.757 | 0.000 |
| always_strongest | max_quality | 14248 | 0.981 | 0.0027 | 1.008 | 0.974 | 0.012 | 0.853 | 0.853 | 0.000 |
| always_strongest | all | 42744 | 0.393 | 0.0519 | 2.033 | 0.974 | 0.012 | 0.853 | 0.744 | 0.000 |
| always_cheapest | cheapest_above_threshold | 14248 | 0.527 | 0.1456 | 0.188 | 0.731 | 0.392 | 0.451 | 0.622 | 0.001 |
| always_cheapest | max_utility | 14248 | 0.183 | 0.2366 | 0.090 | 0.731 | 0.392 | 0.451 | 0.757 | 0.001 |
| always_cheapest | max_quality | 14248 | 0.011 | 0.1173 | 0.029 | 0.731 | 0.392 | 0.451 | 0.853 | 0.001 |
| always_cheapest | all | 42744 | 0.240 | 0.1665 | 0.060 | 0.731 | 0.392 | 0.451 | 0.744 | 0.001 |
