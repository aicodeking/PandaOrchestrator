# Eval: `onnx:artifacts/v2_t150m` on `test` (n=364)

Sources: {'minimal-pair': 78, 'swe-rebench': 53, 'swe-smith': 20, 'synthetic': 148, 'wildchat': 65}  
Latency (batch 1): p50 25.996 ms, p95 144.869 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.750 / 0.882 / 0.035 |
| difficulty | MAE / Spearman / QWK / ECE | 0.870 / 0.831 / 0.823 / 0.020 |
| skills | mean MAE / mean Spearman / mean ECE | 0.841 / 0.769 / 0.106 |
| flags | F1 macro / AUROC macro / ECE | 0.774 / 0.932 / 0.029 |
| checklist | F1 macro / micro / AUROC | 0.719 / 0.800 / 0.911 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.201 / 0.755 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 78 | 0.692 | 0.864 | 0.824 | 0.773 | 0.721 |
| swe-rebench | 53 | 0.811 | 0.892 | 0.171 | 0.637 | 0.375 |
| swe-smith | 20 | 1.000 | 0.699 | 0.477 | 0.250 | 0.488 |
| synthetic | 148 | 0.730 | 0.812 | 0.820 | 0.817 | 0.741 |
| wildchat | 65 | 0.739 | 1.046 | 0.581 | 0.196 | 0.396 |
