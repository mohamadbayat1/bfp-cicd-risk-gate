# 4-5 — Ablation: split strategy and historical features

_Generated: 2026-07-04T14:44:41_

| Configuration | ROC-AUC | PR-AUC | Brier | Condition |
|---|---|---|---|---|
| Diff features only, grouped (cross-project) | 0.5149 | 0.2516 | 0.1887 | Valid ablation (leakage-free; isolates history's contribution) |
| Diff features only, random (within-project) | 0.8332 | 0.6938 | — | DIAGNOSTIC — project-identity leakage; NOT a candidate result |
| Diff + history, grouped (cross-project) — FINAL MODEL | 0.8602 | 0.7489 | 0.1105 | Final reported model |

_Random-split project overlap: 929/930 (99.9%) of test-split projects also appear in train under the random split, vs. 0% by construction under the grouped split -- the concrete mechanism behind the gap above._
