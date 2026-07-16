# Leakage-control verification tests

_Generated: 2026-07-04T14:25:57_

## Leakage drop-list summary

| Category | Count |
|---|---|
| Post-outcome columns (known only during/after the build) | 22 |
| Identifiers / hashes / timestamps | 16 |
| Dropped for missingness / no signal | 4 |
| **Total dropped** | **42** |
| Raw schema columns (TravisTorrent) | 66 |
| **Final feature count in X** | **32** |

## Automated verification tests (fresh run)

_pytest summary: ======================== 9 passed, 3 warnings in 5.22s ========================_

| Test | Result |
|---|---|
| test_no_post_outcome_column_in_X | PASSED |
| test_no_implausible_signal | PASSED |
| test_no_project_overlap_across_splits | PASSED |
| test_inference_uses_saved_encoders_and_medians | PASSED |
| test_thresholds_calibrator_hparams_exclude_test | PASSED |
| test_reproducible_split_and_model | PASSED |
| test_threshold_ordering_and_targets | PASSED |
| test_smoke_three_risk_levels | PASSED |
| test_history_excludes_current_build | PASSED |

## Leakage alarm check

| Check | Value | Threshold | Tripped? |
|---|---|---|---|
| Test ROC-AUC | 0.8602 | >= 0.99 | False |
| Max single-feature importance | 0.2808 | >= 0.5 | False |
