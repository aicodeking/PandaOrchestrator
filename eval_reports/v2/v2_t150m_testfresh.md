# Eval: `onnx:artifacts/v2_t150m` on `test` (n=120)

Sources: {'minimal-pair': 15, 'swe-rebench': 11, 'synthetic': 83, 'wildchat': 11}  
Latency (batch 1): p50 25.679 ms, p95 96.742 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.692 / 0.808 / 0.057 |
| difficulty | MAE / Spearman / QWK / ECE | 0.872 / 0.836 / 0.816 / 0.075 |
| skills | mean MAE / mean Spearman / mean ECE | 1.065 / 0.779 / 0.109 |
| flags | F1 macro / AUROC macro / ECE | 0.800 / 0.931 / 0.042 |
| checklist | F1 macro / micro / AUROC | 0.723 / 0.813 / 0.890 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.196 / 0.775 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 15 | 0.667 | 0.697 | 0.851 | 0.801 | 0.708 |
| swe-rebench | 11 | 0.727 | 0.753 | 0.500 | 0.637 | 0.385 |
| synthetic | 83 | 0.675 | 0.894 | 0.778 | 0.809 | 0.713 |
| wildchat | 11 | 0.818 | 1.066 | 0.618 | 0.303 | 0.436 |
