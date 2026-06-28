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
- **Chosen hyperparameters:** `{'max_depth': 16, 'max_features': 'sqrt', 'min_samples_leaf': 20, 'n_estimators': 400}`  (CV F-beta=0.2952)

## Calibration & decision policy
- Platt scaling (logistic, no class weight) on a held-out calibration subset carved from train.
- Constants: BETA=2, r*=0.8, p*=0.7.
- Thresholds (selected on VALIDATION only): **τ1=0.1376**, **τ2=0.5728**.
  - Recall@τ1 = 0.8001 (target r*=0.8); Precision@τ2 = 0.7000 (target p*=0.7).
  - Fallback used: {'tau1': False, 'tau2': False}.
- Decision: PASS if p<τ1; WARN if τ1≤p<τ2; ROLLBACK if p≥τ2.

## Metrics (threshold-based metrics at τ1; confusion as TP/FP/FN/TN)
| split | ROC-AUC | PR-AUC | Brier | Precision | Recall | F1 | MCC | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|---|
| train | 0.8793 | 0.7876 | 0.1288 | 0.4324 | 0.9348 | 0.5913 | 0.4211 | 141214/185400/9846/204235 |
| val | 0.5698 | 0.2742 | 0.1659 | 0.2247 | 0.8001 | 0.3509 | 0.0548 | 20913/72142/5225/25036 |
| test | 0.5149 | 0.2516 | 0.1887 | 0.2520 | 0.8046 | 0.3838 | 0.0507 | 26787/79491/6506/25885 |

## Three-state decision confusion (test) — actual × decision
| actual \ decision | PASS | WARN | ROLLBACK |
|---|---|---|---|
| pass | 25885 | 79475 | 16 |
| fail | 6506 | 26615 | 172 |

## Leakage alarm check
- Test ROC-AUC = 0.5149 (alarm if ≥ 0.99) → OK
- Max single-feature importance = 0.1262 (alarm if ≥ 0.5) → OK

## Top features — RF importance
| rank | feature | importance |
|---|---|---|
| 1 | gh_sloc | 0.1262 |
| 2 | test_coverage_proxy | 0.1134 |
| 3 | gh_test_lines_per_kloc | 0.1127 |
| 4 | gh_repo_num_commits | 0.1087 |
| 5 | gh_test_cases_per_kloc | 0.1079 |
| 6 | gh_repo_age | 0.0988 |
| 7 | gh_team_size | 0.0970 |
| 8 | gh_asserts_cases_per_kloc | 0.0935 |
| 9 | gh_lang | 0.0381 |
| 10 | git_prev_commit_resolution_status | 0.0323 |
| 11 | gh_num_commits_on_files_touched | 0.0191 |
| 12 | git_num_all_built_commits | 0.0111 |

## Top features — mean |TreeSHAP| (interventional, test sample)
| rank | feature | mean_abs_shap |
|---|---|---|
| 1 | gh_test_cases_per_kloc | 0.02668 |
| 2 | git_prev_commit_resolution_status | 0.02583 |
| 3 | gh_test_lines_per_kloc | 0.02073 |
| 4 | gh_lang | 0.02057 |
| 5 | gh_repo_num_commits | 0.02029 |
| 6 | test_coverage_proxy | 0.01852 |
| 7 | gh_sloc | 0.01570 |
| 8 | gh_team_size | 0.01194 |
| 9 | gh_asserts_cases_per_kloc | 0.01095 |
| 10 | gh_repo_age | 0.00997 |
| 11 | git_num_all_built_commits | 0.00732 |
| 12 | gh_diff_other_files | 0.00393 |

## Figures (in `artifacts/`)
- `calibration_curve.png`
- `threshold_sweep_val.png`
- `feature_importance.png`
- `shap_summary.png`
- `three_state_confusion_test.png`
