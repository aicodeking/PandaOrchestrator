# Eval: `onnx:artifacts/v2_s32m` on `test` (n=364)

Sources: {'minimal-pair': 78, 'swe-rebench': 53, 'swe-smith': 20, 'synthetic': 148, 'wildchat': 65}  
Latency (batch 1): p50 7.638 ms, p95 32.427 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.717 / 0.854 / 0.050 |
| difficulty | MAE / Spearman / QWK / ECE | 0.839 / 0.867 / 0.829 / 0.034 |
| skills | mean MAE / mean Spearman / mean ECE | 0.870 / 0.773 / 0.108 |
| flags | F1 macro / AUROC macro / ECE | 0.770 / 0.930 / 0.031 |
| checklist | F1 macro / micro / AUROC | 0.702 / 0.801 / 0.907 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.189 / 0.841 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 78 | 0.615 | 0.746 | 0.873 | 0.780 | 0.727 |
| swe-rebench | 53 | 0.849 | 0.829 | 0.311 | 0.503 | 0.358 |
| swe-smith | 20 | 1.000 | 0.655 | 0.600 | 0.444 | 0.457 |
| synthetic | 148 | 0.689 | 0.868 | 0.850 | 0.822 | 0.720 |
| wildchat | 65 | 0.708 | 0.947 | 0.629 | 0.259 | 0.404 |
