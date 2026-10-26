# Eval: `onnx:artifacts/v2_s68m` on `test` (n=120)

Sources: {'minimal-pair': 15, 'swe-rebench': 11, 'synthetic': 83, 'wildchat': 11}  
Latency (batch 1): p50 15.71 ms, p95 56.669 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.700 / 0.842 / 0.097 |
| difficulty | MAE / Spearman / QWK / ECE | 0.888 / 0.844 / 0.801 / 0.049 |
| skills | mean MAE / mean Spearman / mean ECE | 1.188 / 0.755 / 0.100 |
| flags | F1 macro / AUROC macro / ECE | 0.808 / 0.935 / 0.045 |
| checklist | F1 macro / micro / AUROC | 0.694 / 0.804 / 0.875 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.214 / 0.733 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 15 | 0.667 | 0.660 | 0.915 | 0.808 | 0.729 |
| swe-rebench | 11 | 0.818 | 0.524 | 0.709 | 0.664 | 0.373 |
| synthetic | 83 | 0.711 | 0.967 | 0.752 | 0.819 | 0.677 |
| wildchat | 11 | 0.545 | 0.975 | 0.746 | 0.100 | 0.348 |
