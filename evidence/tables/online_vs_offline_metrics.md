# Online (live GitHub Actions) vs offline metrics

| evaluation | builds | failure rate | ROC-AUC | PR-AUC | Brier |
|---|---|---|---|---|---|
| online (live campaign, scored) | 271 | 0.196 | 0.6038 | 0.3886 | 0.1328 |
| offline (held-out test) | 138,669 | 0.240 | 0.8602 | 0.7489 | 0.1105 |

Live-vs-recomputed gate-decision mismatches across all 271 scored builds: 0
(the deployed model applied the saved thresholds exactly).
