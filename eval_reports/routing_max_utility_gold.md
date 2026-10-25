# Gold routing, per mode (fixes review finding: utility regret is only valid for max_utility)

`fixed_average` returns the same mean training profile for every task: the floor any real profiler must beat.

| profiler | max_utility pick agreement | max_utility regret (lower is better) | cheapest pick agreement | cheapest below-min-p rate (oracle P) | cheapest cost ratio |
|---|---|---|---|---|---|
| fixed_average | 0.791 | 0.0060 | 0.445 | 0.073 | 1.106 |
| heuristic | 0.818 | 0.0060 | 0.703 | 0.267 | 0.342 |
| knn | 0.838 | 0.0043 | 0.677 | 0.123 | 0.721 |
| t400m | 0.889 | 0.0022 | 0.790 | 0.119 | 0.819 |
| r150m | 0.886 | 0.0025 | 0.778 | 0.125 | 0.761 |
| s68m_soup | 0.878 | 0.0027 | 0.754 | 0.124 | 0.648 |
| s32m_soup | 0.882 | 0.0025 | 0.763 | 0.135 | 0.668 |
| abl32m_direct | 0.881 | 0.0029 | 0.746 | 0.142 | 0.634 |
| abl32m_regret0 | 0.878 | 0.0026 | 0.761 | 0.130 | 0.584 |
| abl32m_pair0 | 0.875 | 0.0028 | 0.750 | 0.119 | 0.743 |
| abl32m_anchor | 0.868 | 0.0030 | 0.711 | 0.111 | 0.869 |
