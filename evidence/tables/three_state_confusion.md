# Three-state decision confusion (test set)

_Generated: 2026-07-04T20:18:57_

| Actual \ Decision | PASS | WARN | ROLLBACK | Total |
|---|---|---|---|---|
| Actual pass (n=105376) | 75097 | 23084 | 7195 | 105376 |
| Actual fail (n=33293) | 5926 | 7554 | 19813 | 33293 |

## Derived operating characteristics

| Metric | Value |
|---|---|
| ROLLBACK precision (of builds sent to ROLLBACK, share that really failed) | 0.7336 |
| Failures flagged (WARN+ROLLBACK as share of all real failures) | 0.8220 |
| Missed failures (real failures sent to PASS, as share of all real failures) | 0.1780 |
| False-pass rate (real failures as share of all PASS decisions) | 0.0731 |
