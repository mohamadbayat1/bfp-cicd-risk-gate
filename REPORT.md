# Chapter 4 — Results (auto-generated from artifacts)

_Seed 42. Versions: python=3.12.10, numpy=2.4.6, pandas=3.0.3, scikit_learn=1.9.0, shap=0.52.0, joblib=1.5.3._

## Dataset & target
- Builds (after dedup to one row/build, dropping `started`): **925,896**
- Target: `y=1` if `tr_status != 'passed'` (failed/errored/canceled), else 0.
- Class balance: 234,732 failures / 691,164 passes (failure rate **0.2535**).

## Split (grouped by project, no project on two sides)
| split | builds | projects | failure_rate |
|---|---|---|---|
| train | 663,911 | 662 | 0.2640 |
| train_fit | 540,695 | 562 | 0.2794 |
| calib | 123,216 | 100 | 0.1967 |
| val | 123,316 | 143 | 0.2120 |
| test | 138,669 | 143 | 0.2401 |

## Model & tuning
- RandomForest (gini, class_weight=balanced, random_state=42).
- Grid search: StratifiedGroupKFold(5), scoring fbeta(beta=2), on a stratified subsample of 80,000 (final model refit on the full training set).
- Search space: `{'n_estimators': [200, 400], 'max_depth': [16, None], 'min_samples_leaf': [5, 20], 'max_features': ['sqrt']}`
- **Chosen hyperparameters:** `{'max_depth': 16, 'max_features': 'sqrt', 'min_samples_leaf': 20, 'n_estimators': 400}`  (CV F-beta=0.7313)

## Calibration & decision policy
- Platt scaling (logistic, no class weight) on a held-out calibration subset carved from train.
- Constants: BETA=2, r*=0.8, p*=0.7.
- Thresholds (selected on VALIDATION only): **τ1=0.1095**, **τ2=0.4769**.
  - Recall@τ1 = 0.8000 (target r*=0.8); Precision@τ2 = 0.7000 (target p*=0.7).
  - Fallback used: {'tau1': False, 'tau2': False}.
- Decision: PASS if p<τ1; WARN if τ1≤p<τ2; ROLLBACK if p≥τ2.

## Metrics (threshold-based metrics at τ1; confusion as TP/FP/FN/TN)
| split | ROC-AUC | PR-AUC | Brier | Precision | Recall | F1 | MCC | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|---|
| train | 0.9152 | 0.8527 | 0.0971 | 0.5432 | 0.9070 | 0.6794 | 0.5498 | 137011/115231/14049/274404 |
| val | 0.8479 | 0.6898 | 0.1093 | 0.4336 | 0.8000 | 0.5624 | 0.4346 | 20911/27313/5227/69865 |
| test | 0.8601 | 0.7477 | 0.1107 | 0.4767 | 0.8208 | 0.6031 | 0.4650 | 27328/30005/5965/75371 |

## Three-state decision confusion (test) — actual × decision
| actual \ decision | PASS | WARN | ROLLBACK |
|---|---|---|---|
| pass | 75371 | 22937 | 7068 |
| fail | 5965 | 7579 | 19749 |

## Leakage alarm check
- Test ROC-AUC = 0.8601 (alarm if ≥ 0.99) → OK
- Max single-feature importance = 0.2349 (alarm if ≥ 0.5) → OK

## Top features — RF importance
| rank | feature | importance |
|---|---|---|
| 1 | hist_prev_status | 0.2349 |
| 2 | hist_consec_fail | 0.2238 |
| 3 | hist_fail_rate_5 | 0.1807 |
| 4 | hist_fail_rate_20 | 0.1330 |
| 5 | hist_fail_rate_all | 0.0808 |
| 6 | hist_build_seq | 0.0159 |
| 7 | gh_sloc | 0.0134 |
| 8 | gh_test_cases_per_kloc | 0.0125 |
| 9 | gh_repo_num_commits | 0.0123 |
| 10 | test_coverage_proxy | 0.0116 |
| 11 | gh_test_lines_per_kloc | 0.0111 |
| 12 | gh_asserts_cases_per_kloc | 0.0103 |

## Top features — mean |TreeSHAP| (interventional, test sample)
| rank | feature | mean_abs_shap |
|---|---|---|
| 1 | hist_consec_fail | 0.05943 |
| 2 | hist_prev_status | 0.05425 |
| 3 | hist_fail_rate_5 | 0.04373 |
| 4 | hist_fail_rate_20 | 0.03917 |
| 5 | hist_fail_rate_all | 0.03148 |
| 6 | git_prev_commit_resolution_status | 0.01377 |
| 7 | git_num_all_built_commits | 0.01027 |
| 8 | gh_diff_other_files | 0.00969 |
| 9 | gh_diff_files_modified | 0.00568 |
| 10 | gh_diff_files_added | 0.00540 |
| 11 | gh_is_pr | 0.00528 |
| 12 | hist_build_seq | 0.00415 |

## Figures (in `artifacts/`)
- `calibration_curve.png`
- `threshold_sweep_val.png`
- `feature_importance.png`
- `shap_summary.png`
- `three_state_confusion_test.png`
