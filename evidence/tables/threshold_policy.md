# Decision-threshold policy

_Generated: 2026-07-04T20:18:57_

| Quantity | Value |
|---|---|
| tau1 (PASS / WARN boundary) | 0.1119 |
| tau2 (WARN / ROLLBACK boundary) | 0.4662 |
| r* (target recall for tau1) | 0.80 |
| p* (target precision for tau2) | 0.70 |
| Recall@tau1 (validation) | 0.8000 |
| Precision@tau2 (validation) | 0.7000 |
| Fallback used for tau1? | False |
| Fallback used for tau2? | False |

_tau1 < tau2 holds: True. Both recall/precision targets were met without a fallback firing, but at the exact boundary of the feasible region (Recall@tau1 == r* to 2 decimals) -- see HANDOFF.md's honest note on fallback risk._
