# Eval: `onnx:artifacts/v2_s68m` on `test` (n=364)

Sources: {'minimal-pair': 78, 'swe-rebench': 53, 'swe-smith': 20, 'synthetic': 148, 'wildchat': 65}  
Latency (batch 1): p50 16.241 ms, p95 68.756 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.742 / 0.876 / 0.042 |
| difficulty | MAE / Spearman / QWK / ECE | 0.883 / 0.833 / 0.813 / 0.038 |
| skills | mean MAE / mean Spearman / mean ECE | 0.905 / 0.752 / 0.103 |
| flags | F1 macro / AUROC macro / ECE | 0.766 / 0.927 / 0.036 |
| checklist | F1 macro / micro / AUROC | 0.699 / 0.792 / 0.900 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.216 / 0.772 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 78 | 0.705 | 0.876 | 0.806 | 0.762 | 0.708 |
| swe-rebench | 53 | 0.849 | 0.790 | 0.278 | 0.576 | 0.372 |
| swe-smith | 20 | 1.000 | 0.648 | 0.514 | 0.333 | 0.445 |
| synthetic | 148 | 0.696 | 0.879 | 0.809 | 0.824 | 0.714 |
| wildchat | 65 | 0.723 | 1.046 | 0.639 | 0.149 | 0.350 |
