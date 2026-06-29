# MEMORY.md — global/architectural decisions

Records only durable decisions (target, leakage, split, hyperparameters, calibration/threshold
design, deviations). For each: what changed, why, which files, how to revert.

## D1 — Target definition
- **What:** `y=0` if `tr_status=="passed"`, else `y=1` (failed/errored/canceled). Drop
  `tr_status=="started"` (outcome unknown) and null-status/null-id rows.
- **Why:** binary failure prediction per Chapter 3; `started` builds have no known outcome.
- **Files:** data loader (Phase 3), `config.py`.
- **Revert:** change the positive-class mapping in `config.py`.

## D2 — Unit of analysis = build (dedup), not job
- **What:** dataset is 3,881,992 job-rows = 925,897 builds (~4.19 jobs/build). Status is
  constant within every build. Dedup to one row per `tr_build_id` (keep first).
- **Why:** features are build-level (identical across a build's jobs); keeping job-rows
  duplicates data, inflates metrics, and lets one build's rows straddle the split (row leakage).
- **Files:** data loader.
- **Revert:** skip the dedup step (NOT recommended — reintroduces leakage).

## D3 — Leakage drop list (floor + extensions)
- **What:** drop all `tr_log_*`, `tr_duration`, `tr_jobs`, `tr_prev_build`,
  `tr_virtual_merged_into`, all ids/hashes/timestamps, and `tr_status` (target). Notable strong
  leak: `tr_log_status` (build status parsed from log). `gh_project_name`/`tr_build_id` kept
  ONLY as group/dedup keys, never in X. Full list in PLAN.md.
- **Why:** zero leakage is the top priority; these are known only during/after the build, or are
  identifiers. Univariate scan: no legitimate feature exceeds AUC 0.552 → feature set is clean.
- **Files:** `config.py` (DROP_COLS, FEATURES), leakage tests.
- **Revert:** edit `config.py` lists (any addition to X must pass the "exists only after build?" test).

## D4 — Feature set + engineered features
- **What:** ~26 pre-build features (20 numeric + 4 categorical + churn_ratio,
  test_coverage_proxy). Dropped for missingness/no-signal: `gh_num_commits_in_push` (100% NA),
  `gh_num_issue_comments`, `gh_num_pr_comments`, `gh_description_complexity` (~79% NA, ~0.50 AUC).
- **Why:** keep only pre-build, informative columns; engineered features per spec.
- **Files:** `config.py`, preprocessing.
- **Revert:** restore dropped names to FEATURES in `config.py`.

## D5 — Split strategy = grouped by project
- **What:** GroupShuffleSplit/StratifiedGroupKFold by `gh_project_name`, 70/15/15, seed 42.
  Calibration subset carved grouped within train.
- **Why:** successive builds of one project → random split leaks project identity; grouped split
  = no project on both sides = honest generalization test + strict leakage guard (test #3).
- **Files:** data loader / splitter.
- **Revert:** switch to StratifiedShuffleSplit (NOT recommended — reintroduces project leakage).

## D6 — Model + tuning
- **What:** RandomForest(gini, class_weight="balanced", random_state=42, n_jobs=-1).
  GridSearchCV 5-fold StratifiedGroupKFold, scoring F-beta (BETA=2), on ~100k stratified
  subsample of train; final refit on full train. Search space in PLAN.md.
- **Why:** Chapter-3 method; subsample keeps search tractable on ~3.9M rows.
- **Files:** training script, `config.py`.
- **Revert:** edit search space / BETA in `config.py`.

## D7 — Calibration + thresholds
- **What:** Platt scaling (LogisticRegression, no class_weight) on grouped calibration subset.
  Thresholds on VALIDATION only: τ1 = largest τ with Recall≥r* (0.80); τ2 = smallest τ>τ1 with
  Precision≥p* (0.70); enforce τ1<τ2. **Fallbacks:** τ1→median pred prob, τ2→99th pct pred prob.
- **Why:** recall-favoring, coherent policy per Chapter 3; F1/MCC reported but NOT used to pick τ.
- **Files:** calibration + threshold scripts, `config.py`.
- **Revert:** adjust r*/p*/BETA in `config.py`; fallback usage logged here when triggered.
- **Fallback log:** (none yet — to be filled if a target is unreachable in Phase 3.)

## D8 — Deviations from Chapter-3 architecture
- See PLAN.md "DEVIATIONS / EXTENSIONS" (9 items): schema remap, build-unit dedup, drop
  `started`, log-derived categoricals excluded, extra missingness drops, grouped split, grouped
  calibration carve, proposed policy constants + fallbacks, subsampled grid search.
- **Why:** keep code and thesis text consistent; all driven by the real data + zero-leakage rule.

## D9 — KEY METHODOLOGICAL FINDING: failure signal is project-specific
- **What:** with diff-level features only, leakage-free grouped (cross-project) test
  ROC-AUC = 0.515 (≈ random); the SAME features/model on a naive random split = 0.845.
  The gap is project identity leaking across the split (row-level leakage the spec warns of).
- **Why it matters:** confirms zero column-leakage (no transferable signal once projects are
  held out) AND demonstrates why random splits inflate TravisTorrent results. Pipeline
  verified correct (random split = strong), so 0.515 is a feature finding, not a bug.
- **Files:** PLAN.md (ablation table), REPORT.md.

## D10 — RESOLUTION: leakage-free historical features (FINAL model)
- **What:** added 6 per-project history features (`hist_prev_status`, `hist_fail_rate_5/20/all`,
  `hist_consec_fail`, `hist_build_seq`), each computed from STRICTLY PRIOR builds via a
  per-project shift, ordered by `tr_build_number` (used only for ordering, dropped from X).
  Final full-run grouped/cross-project test: **ROC-AUC 0.860, PR-AUC 0.749, Brier 0.111**,
  CV F-beta 0.733. Thresholds τ1=0.1119, τ2=0.4662 (no fallback; Recall@τ1=0.80≥0.80,
  ROLLBACK precision 0.734≥0.70). Chosen RF: depth16 / **max_features=0.4** / leaf20 / 400.
  Max feature importance 0.281 (<0.50) — no alarm. **Full 24-candidate** grid search
  (StratifiedGroupKFold, 5-fold; per-candidate table in `artifacts/grid_search.json`);
  final fit on full train. run_offline supports `--resume-grid` (grid checkpointed).
- **Why leakage-free:** history uses only past outcomes (known at trigger time); temporal
  order validated (Spearman 1.0 vs build_id; shift matches manual); test #9 guards the shift.
- **Files:** `bfp/config.py` (USE_HISTORY, FEATURES_HISTORICAL, ORDER_COLS, trimmed
  PARAM_GRID), `bfp/data.py` (add_history), `bfp/preprocess.py` (NUMERIC_COLS),
  `tests/test_pipeline.py` (test #9). Artifacts regenerated.
- **Revert:** set `USE_HISTORY=False` in `config.py` (drops history, falls back to the
  0.515 diff-only model) and restore the wider PARAM_GRID.

## Environment notes
- Installed: numpy 2.5.0, pandas 3.0.3, Python 3.12.10. **Missing (install Phase 3):**
  scikit-learn, shap, matplotlib, joblib.
- Working dir is NOT yet a git repo → `git init` + branch `thesis-pipeline` in Phase 3.
