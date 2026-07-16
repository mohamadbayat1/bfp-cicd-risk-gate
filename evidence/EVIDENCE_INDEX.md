# Chapter 4 — Evidence Pool (design the chapter yourself)

**Read this first.** This folder is the complete, verified evidence for writing the
results chapter of the thesis. It is deliberately **FLAT and structure-free**: there is
**NO prescribed section or subsection layout here**. The grouping below is by *topic of
evidence*, not by chapter order. **You decide the chapter's sections, subsections,
ordering, and what to include or omit** — that is your job, not something dictated here.

Rules:
- **Never invent a number.** Every value you write must come from a table/figure in this
  folder (or the "verified key numbers" block below, which is copied from them).
- Tables are Markdown; figures are PNG (insert as figures). Filenames describe *content*,
  not any section number.
- Reproduction context (how the numbers were produced, the method/workflow) is in the
  repo-root `RESULTS.md`. Read it for the pipeline; it does not prescribe chapter
  structure either.
- Everything here is the FINAL/correct generation. Superseded material (an earlier
  5-commit demo case study, an older LLM report batch) has been removed on purpose — do
  not go looking for it.

---

## Available evidence, by topic

### Dataset & data preparation
- `tables/dataset_overview.md` — raw job rows, builds after aggregation, class counts, failure rate, project count
- `tables/data_split_by_project.md` — train / model-fit / calibration / validation / test sizes, projects, failure rates
- `tables/leakage_verification_tests.md` — the 9 automated verification tests and their assertions
- `figures/class_balance_4way.png` — passed/failed/errored/canceled distribution
- `figures/failure_rate_by_language.png` — failure rate per programming language

### Model, tuning & calibration
- `tables/final_model_config.md` — model, criterion, class weighting, CV, search metric, chosen hyperparameters
- `tables/grid_search_top_configs.md` — top-8 of 24 grid candidates (the min_samples_leaf=20 finding)
- `figures/grid_search_top_configs.png` — the same, as a chart
- `figures/calibration_curve.png` — reliability curve (validation + test)
- `tables/threshold_policy.md` — tau1/tau2, targets r*/p*, achieved recall/precision, fallback flags
- `figures/threshold_sweep.png` — precision/recall/F1 vs threshold with tau1/tau2 marked

### Offline evaluation (held-out test, unseen projects)
- `tables/metrics_by_split.md` — ROC-AUC / PR-AUC / Brier / Precision / Recall / F1 / MCC across train/val/test
- `figures/roc_curve_test.png`, `figures/pr_curve_test.png`, `figures/prob_distribution_test_offline.png`, `figures/metrics_comparison.png`
- `tables/three_state_confusion.md` + `figures/three_state_confusion_heatmap.png` — actual × decision, plus derived rates
- `tables/rf_feature_importance_top10.md`, `tables/shap_top8.md` — feature importance (RF and TreeSHAP)
- `figures/rf_importance_bar.png`, `figures/shap_summary.png`

### Ablation (the central methodological finding)
- `tables/ablation_split_and_history.md` — diff-only/grouped vs diff-only/random vs diff+history/grouped
- `figures/ablation_summary.png`

### Live deployment (GitHub Actions) + online evaluation campaign
- `figures/deployment_architecture.png` — the 3-layer framework deployed in a real pipeline (push → gate → tests)
- `tables/online_campaign_overview.md` — protocol (9 repos × 50 commits, shadow mode, warm-up) + operating characteristics + latency
- `tables/online_vs_offline_metrics.md` — live campaign metrics next to the offline reference
- `tables/online_failure_decomposition.md` — continuation vs first-of-streak failures (the key live finding)
- `figures/online_cold_start_curve.png`, `figures/online_prob_distribution.png`

### Language-analysis (LLM) layer
- `llm_reports/llm_report_warn_example.md` — one real WARN build report (verbatim model output + input payload)
- `llm_reports/llm_report_rollback_example.md` — one real ROLLBACK build report
- The prompt design/spec lives in repo-root `LLM_PROMPT.md` (the production prompt; ignore any section-number pointers inside it).

---

## Verified key numbers (all copied from the files above — safe to cite)

- Dataset: 3,881,992 raw job rows → **925,896 builds** / **948 projects**; failures 234,732; **failure rate 0.2535**; 4-way: passed 74.65% / failed 18.06% / errored 6.94% / canceled 0.35%.
- Features: **32** = 24 raw + 2 engineered (churn_ratio, test_coverage_proxy) + 6 history (hist_*). Dropped **42 of 66** raw columns (22 post-outcome + 16 ids/time + 4 missingness).
- Split (grouped by project, 70/15/15): test = **138,669 builds / 143 unseen projects**.
- Grid: 24 candidates, StratifiedGroupKFold(5), F-beta(β=2), 80k subsample. Best CV F-beta **0.7328**; chosen **n_estimators=400, max_depth=16, min_samples_leaf=20, max_features=0.4**.
- Thresholds (validation only): **τ1 = 0.1119, τ2 = 0.4662**; recall@τ1 = 0.8000, precision@τ2 = 0.7000; no fallback.
- Offline test: **ROC-AUC 0.8602 / PR-AUC 0.7489 / Brier 0.1105**; base rate 0.2401.
- Three-state (test): ROLLBACK precision **0.7336**; failures flagged **82.2%**; false-pass **7.3%** (0.0731).
- Top features (RF importance): hist_consec_fail 0.2808, hist_prev_status 0.2632, hist_fail_rate_5 0.1490, hist_fail_rate_20 0.1022, hist_fail_rate_all 0.0568 (~85% from the 5 history features).
- Ablation: diff-only grouped **0.5149** ; diff-only random **0.8332** (leakage, 929/930 projects overlap) ; diff+history grouped **0.8602**.
- Leakage alarms: test ROC-AUC 0.8602 < 0.99 ✓ ; max feature importance 0.2808 < 0.50 ✓. 9 tests pass (5.22 s).
- Reproducibility: python 3.12.10, numpy 2.4.6, pandas 3.0.3, scikit-learn 1.9.0, shap 0.52.0, joblib 1.5.3, seed 42.
- Online campaign: 9 repos × 50 = **450 runs**, 179 warm-up, **271 scored** (failure rate 0.196). Overall **ROC-AUC 0.6038** / PR-AUC 0.3886 / Brier 0.1328. Decomposition: continuation **30/30 flagged, AUC 0.936**; first-of-streak **0/23, AUC 0.170**; ~43% of failures were onsets. Flagged 56.6%, ROLLBACK precision 0.531, false-pass 11.7%, 0 decision mismatches. Median gate latency ~37 s (~5 s scoring).
- LLM model: an open-weight Llama-family model (Llama-3.3-Nemotron-Super-49B) via an API; called only for WARN/ROLLBACK; true label never given to the model.
