# Online evaluation campaign — protocol & operating characteristics

Protocol: 9 independent public GitHub repos, 50 real commits each pushed one at a time;
every commit ran a SHADOW risk-gate workflow (records decision, never blocks) followed by
the real pytest suite -> every build has a gate decision AND a ground-truth label. Commit
sequences scripted (seeded, reproducible) with realistic clustered failures; labels are
real test outcomes, never scripted. First 20 runs per repo = warm-up (excluded). Same
saved model / calibrator / thresholds (tau1=0.1119, tau2=0.4662) as the offline evaluation.

| quantity | value |
|---|---|
| repos | 9 |
| total real GitHub Actions runs | 450 |
| warm-up runs excluded (20/repo) | 179 |
| scored builds | 271 |
| scored failure rate | 0.196 |
| failures flagged (WARN+ROLLBACK) | 56.6% |
| ROLLBACK precision | 0.531 |
| false-pass rate | 11.7% |
| median gate-job latency | ~37 s (of which ~5 s model scoring; rest is runner setup) |
