# Eval: `onnx:artifacts/v2_s32m` on `test` (n=120)

Sources: {'minimal-pair': 15, 'swe-rebench': 11, 'synthetic': 83, 'wildchat': 11}  
Latency (batch 1): p50 10.186 ms, p95 46.189 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.683 / 0.808 / 0.086 |
| difficulty | MAE / Spearman / QWK / ECE | 0.883 / 0.863 / 0.807 / 0.063 |
| skills | mean MAE / mean Spearman / mean ECE | 1.142 / 0.773 / 0.108 |
| flags | F1 macro / AUROC macro / ECE | 0.800 / 0.939 / 0.044 |
| checklist | F1 macro / micro / AUROC | 0.706 / 0.813 / 0.885 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.189 / 0.883 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 15 | 0.533 | 0.592 | 0.950 | 0.786 | 0.723 |
| swe-rebench | 11 | 0.909 | 0.638 | 0.682 | 0.672 | 0.374 |
| synthetic | 83 | 0.675 | 0.953 | 0.801 | 0.815 | 0.703 |
| wildchat | 11 | 0.727 | 1.000 | 0.736 | 0.242 | 0.328 |
