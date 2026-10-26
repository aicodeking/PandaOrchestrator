# Eval: `onnx:artifacts/v2_32_base_onnx` on `test` (n=120)

Sources: {'minimal-pair': 15, 'swe-rebench': 11, 'synthetic': 83, 'wildchat': 11}  
Latency (batch 1): p50 4.564 ms, p95 17.64 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.642 / 0.808 / 0.074 |
| difficulty | MAE / Spearman / QWK / ECE | 0.838 / 0.870 / 0.824 / 0.058 |
| skills | mean MAE / mean Spearman / mean ECE | 1.161 / 0.761 / 0.105 |
| flags | F1 macro / AUROC macro / ECE | 0.803 / 0.935 / 0.043 |
| checklist | F1 macro / micro / AUROC | 0.706 / 0.807 / 0.887 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.202 / 0.825 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 15 | 0.533 | 0.595 | 0.953 | 0.807 | 0.753 |
| swe-rebench | 11 | 0.818 | 0.466 | 0.836 | 0.644 | 0.368 |
| synthetic | 83 | 0.651 | 0.907 | 0.814 | 0.814 | 0.696 |
| wildchat | 11 | 0.545 | 1.011 | 0.746 | 0.220 | 0.286 |
