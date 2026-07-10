# 4-6-5 — Real-world GitHub Actions case study (5 real runs)

_Generated: 2026-07-04T15:37:19_

_Repo: https://github.com/novavisionstudio-byte/bfp-cicd-risk-gate-demo -- every row is a real, separately-pushed commit that triggered a real GitHub Actions run of `.github/workflows/risk-gate.yml`._

| # | Commit | Nature | Gate decision | p(fail) | Top SHAP feature | Actual test outcome |
|---|---|---|---|---|---|---|
| 2 | Add factorial function with tests | clean, tested | **PASS** | 0.0743 | hist_build_seq=0 (SHAP +0.1067) | pass |
| 3 | Expose factorial via the API | clean, tested | **PASS** | 0.0786 | hist_build_seq=1 (SHAP +0.0718) | pass |
| 4 | Add stats module (large diff, light tests) | large diff, weak tests | **PASS** | 0.0805 | hist_build_seq=2 (SHAP +0.0498) | pass |
| 5 | Handle divide-by-zero by returning 0 (removes the exception) | small diff, breaks behavior | **PASS** | 0.0508 | hist_fail_rate_all=0 (SHAP -0.0447) | FAIL (2 tests) |
| 6 | Fix: restore ValueError on divide-by-zero | fix | **ROLLBACK** | 0.5137 | hist_prev_status=1 (SHAP +0.1664) | pass (job skipped -- gate ROLLBACK stopped it first) |

_Thresholds: tau1=0.1119, tau2=0.4662._

**Note on commit 1.** Its own live run is excluded here: two infrastructure bugs (a `pytest` invocation difference between local and CI, then a force-push history-resolution edge case) were found and fixed live against it, and the resulting failed runs transiently *contaminated* the live history signal (the model correctly, if misleadingly, saw 2 prior 'failures' that were actually my own CI-config bugs, not application risk, and returned ROLLBACK). Those runs were deleted once the fix landed; the clean case study begins at commit 2. This is itself a genuine, worth-reporting finding: transient CI infrastructure failures pollute the live history features exactly as much as real application failures, until cleaned up.
