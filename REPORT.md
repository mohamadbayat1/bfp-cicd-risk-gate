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
- Search space: `{'n_estimators': [200, 400], 'max_depth': [None, 16], 'min_samples_leaf': [1, 5, 20], 'max_features': ['sqrt', 0.4]}`
- **Chosen hyperparameters:** `{'max_depth': 16, 'max_features': 0.4, 'min_samples_leaf': 20, 'n_estimators': 400}`  (CV F-beta=0.7328)

## Calibration & decision policy
- Platt scaling (logistic, no class weight) on a held-out calibration subset carved from train.
- Constants: BETA=2, r*=0.8, p*=0.7.
- Thresholds (selected on VALIDATION only): **τ1=0.1119**, **τ2=0.4662**.
  - Recall@τ1 = 0.8000 (target r*=0.8); Precision@τ2 = 0.7000 (target p*=0.7).
  - Fallback used: {'tau1': False, 'tau2': False}.
- Decision: PASS if p<τ1; WARN if τ1≤p<τ2; ROLLBACK if p≥τ2.

## Metrics (threshold-based metrics at τ1; confusion as TP/FP/FN/TN)
| split | ROC-AUC | PR-AUC | Brier | Precision | Recall | F1 | MCC | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|---|
| train | 0.9225 | 0.8621 | 0.0940 | 0.5522 | 0.9163 | 0.6892 | 0.5653 | 138423/112230/12637/277405 |
| val | 0.8477 | 0.6902 | 0.1092 | 0.4342 | 0.8000 | 0.5629 | 0.4353 | 20911/27247/5227/69931 |
| test | 0.8602 | 0.7489 | 0.1105 | 0.4747 | 0.8220 | 0.6019 | 0.4634 | 27367/30279/5926/75097 |

## Three-state decision confusion (test) — actual × decision
| actual \ decision | PASS | WARN | ROLLBACK |
|---|---|---|---|
| pass | 75097 | 23084 | 7195 |
| fail | 5926 | 7554 | 19813 |

## Leakage alarm check
- Test ROC-AUC = 0.8602 (alarm if ≥ 0.99) → OK
- Max single-feature importance = 0.2808 (alarm if ≥ 0.5) → OK

## Top features — RF importance
| rank | feature | importance |
|---|---|---|
| 1 | hist_consec_fail | 0.2808 |
| 2 | hist_prev_status | 0.2632 |
| 3 | hist_fail_rate_5 | 0.1490 |
| 4 | hist_fail_rate_20 | 0.1022 |
| 5 | hist_fail_rate_all | 0.0568 |
| 6 | hist_build_seq | 0.0159 |
| 7 | gh_repo_num_commits | 0.0132 |
| 8 | gh_sloc | 0.0126 |
| 9 | test_coverage_proxy | 0.0123 |
| 10 | gh_repo_age | 0.0118 |
| 11 | gh_test_cases_per_kloc | 0.0107 |
| 12 | gh_num_commits_on_files_touched | 0.0105 |

## Top features — mean |TreeSHAP| (interventional, test sample)
| rank | feature | mean_abs_shap |
|---|---|---|
| 1 | hist_consec_fail | 0.06701 |
| 2 | hist_prev_status | 0.05592 |
| 3 | hist_fail_rate_20 | 0.03961 |
| 4 | hist_fail_rate_5 | 0.03670 |
| 5 | hist_fail_rate_all | 0.03511 |
| 6 | git_prev_commit_resolution_status | 0.01470 |
| 7 | git_num_all_built_commits | 0.01202 |
| 8 | gh_diff_other_files | 0.01040 |
| 9 | gh_is_pr | 0.00589 |
| 10 | gh_diff_files_added | 0.00565 |
| 11 | gh_diff_files_modified | 0.00520 |
| 12 | hist_build_seq | 0.00433 |

## Figures (in `artifacts/`)
- `calibration_curve.png`
- `threshold_sweep_val.png`
- `feature_importance.png`
- `shap_summary.png`
- `three_state_confusion_test.png`
