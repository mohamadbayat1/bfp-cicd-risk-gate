# Online metrics (scored builds, saved thresholds tau1=0.1119 / tau2=0.4662)

| setting | n | failure rate | ROC-AUC | PR-AUC | Brier |
|---|---|---|---|---|---|
| online campaign | 271 | 0.1956 | 0.6038 | 0.3886 | 0.1328 |
| offline held-out test (reference) | 138,669 | 0.2401 | 0.8602 | 0.7489 | 0.1105 |

## Three-state confusion (actual x decision)

| actual \ decision | PASS | WARN | ROLLBACK |
|---|---|---|---|
| pass (n=218) | 174 | 21 | 23 |
| fail (n=53) | 23 | 4 | 26 |

- ROLLBACK precision: **0.5306**
- failures flagged (WARN+ROLLBACK): **0.566**
- false-pass rate (fails inside PASS decisions): **0.1168**

_live-vs-rederived decision mismatches: 0_
