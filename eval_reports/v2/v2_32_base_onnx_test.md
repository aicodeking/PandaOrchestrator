# Eval: `onnx:artifacts/v2_32_base_onnx` on `test` (n=364)

Sources: {'minimal-pair': 78, 'swe-rebench': 53, 'swe-smith': 20, 'synthetic': 148, 'wildchat': 65}  
Latency (batch 1): p50 5.075 ms, p95 18.405 ms

## Profiler

| head | metric | value |
|---|---|---|
| category | acc / top2 / ECE | 0.725 / 0.860 / 0.038 |
| difficulty | MAE / Spearman / QWK / ECE | 0.811 / 0.874 / 0.833 / 0.042 |
| skills | mean MAE / mean Spearman / mean ECE | 0.889 / 0.763 / 0.112 |
| flags | F1 macro / AUROC macro / ECE | 0.780 / 0.935 / 0.034 |
| checklist | F1 macro / micro / AUROC | 0.707 / 0.796 / 0.905 |
| out_tokens | MAE log10 / p10-p90 coverage | 0.199 / 0.797 |

### By source

| source | n | cat acc | diff MAE | diff Spearman | flags F1 | checklist F1 |
|---|---|---|---|---|---|---|
| minimal-pair | 78 | 0.679 | 0.791 | 0.884 | 0.783 | 0.745 |
| swe-rebench | 53 | 0.811 | 0.748 | 0.461 | 0.560 | 0.351 |
| swe-smith | 20 | 1.000 | 0.686 | 0.573 | 0.333 | 0.451 |
| synthetic | 148 | 0.703 | 0.832 | 0.851 | 0.839 | 0.720 |
| wildchat | 65 | 0.677 | 0.876 | 0.689 | 0.237 | 0.399 |
