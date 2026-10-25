| metric | heuristic@gold | knn@gold | heuristic@test |
|---|---|---|---|
| category acc | 0.498 | 0.579 | 0.531 |
| category top2 | 0.660 | 0.719 | 0.732 |
| difficulty MAE | 1.342 | 1.099 | 1.494 |
| difficulty Spearman | 0.566 | 0.487 | 0.634 |
| difficulty QWK | 0.360 | 0.463 | 0.437 |
| difficulty vs IRT (Spearman) | 0.057 | 0.033 | - |
| skills MAE (mean) | 1.237 | 0.940 | 1.586 |
| flags F1 macro | 0.266 | 0.362 | 0.557 |
| flags AUROC macro | 0.641 | 0.710 | 0.786 |
| checklist F1 macro | 0.248 | 0.392 | 0.338 |
| out_tokens MAE log10 | 0.271 | 0.290 | 0.302 |
| ECE category | 0.202 | 0.096 | 0.172 |
| ECE difficulty | 0.127 | 0.050 | 0.132 |
| ECE flags | 0.125 | 0.078 | 0.152 |
| ECE checklist | 0.116 | 0.070 | 0.175 |
| latency p50 ms | 0.582 | 37.000 | 1.304 |
| latency p95 ms | 5.368 | 98.180 | 9.833 |
| routing[all] pick_agreement | 0.834 | 0.833 | 0.784 |
| routing[all] utility_regret | 0.027 | -0.001 | 0.027 |
| routing[all] cost_ratio | 0.870 | 0.960 | 0.735 |
| routing[all] p_success | 0.906 | 0.937 | 0.851 |
| routing[all] below_min_p_rate | 0.113 | 0.060 | 0.219 |
| routing[all] pq_quality | 0.706 | 0.749 | 0.673 |
| routing[all] infeasible_rate | 0.000 | 0.000 | 0.000 |

Fixed-pick baselines (all, from heuristic run):

| policy | pick_agreement | utility_regret | cost_ratio | p_success | below_min_p_rate | pq_quality | infeasible_rate |
|---|---|---|---|---|---|---|---|
| always_strongest | 0.393 | 0.052 | 2.033 | 0.974 | 0.012 | 0.853 | 0.000 |
| always_cheapest | 0.240 | 0.167 | 0.060 | 0.731 | 0.392 | 0.451 | 0.001 |
