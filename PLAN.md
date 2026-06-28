# PLAN.md — AI-in-CI/CD Build-Failure Prediction Pipeline

**Progress: 9/35 (Phase 1 complete; Phase 2 awaiting user approval)**
**Phase: 2 (Plan & propose) — STOP here for approval before Phase 3.**

This pipeline predicts, before a build finishes, the probability a CI build will FAIL,
and maps that probability to PASS / WARN / ROLLBACK. Two phases: offline training,
online inference. Highest priority = ZERO data leakage.

---

## DATASET PROFILE (Phase 1 — verified directly from the file)

- **File:** `final-2017.csv`, 3.55 GB. Canonical TravisTorrent schema, **66 columns**.
- **Header DIFFERS from the spec's reference header** (spec warned this). The real schema
  uses `tr_log_*` prefixes for the build-log-derived columns and different names throughout.
  A name-remapping was required (see Leakage list and Feature list below).
- **Row count: 3,881,992** (far above the spec's ~1–2M estimate).
- **Unit of analysis is a JOB, not a build.** Each Travis build expands to ~4.19 rows
  (one per job). Head sample: build `3154` appears as 4 rows differing only in
  `tr_job_id` / `tr_log_*` / `tr_duration`; all `gh_*` / `git_diff_*` feature values are
  identical across a build's jobs.
- **Unique builds: 925,897.** Status is **constant within every build** (0 builds with
  inconsistent status across jobs) → safe to deduplicate to one row per build.
- **Target column:** `tr_status`. Values (job-level): passed 2,810,783 / failed 751,531 /
  errored 279,483 / canceled 40,192 / **started 3** (in-progress, label undefined).
- **Class balance (build-level, after dedup):** passed 691,164 (74.65%),
  failed 167,204, errored 64,256, canceled 3,272, started 1.
  → **failure rate = 0.2535** (target=1 share ≈ 25.4%). Healthy; no extreme imbalance.
- **Projects:** 948 unique (`gh_project_name`). Languages present: go, java, python, ruby.
- **Data quality:** leading rows are clean (no empty/malformed head observed); all profiled
  numeric columns coerce to numeric with 0 non-coercible non-null values. `NA` and `""`
  are the missing tokens.

### Target definition (stated explicitly)
`y = 0` if `tr_status == "passed"` (success); `y = 1` otherwise
(failed / errored / canceled = failure). Builds with `tr_status == "started"` are **dropped**
(outcome not yet known). Rows with null `tr_status` or null `tr_build_id` are dropped.

### LEAKAGE SCAN (univariate strength vs target, on a 116,460-row stratified sample)
Symmetric AUC (max(auc, 1-auc)); 0.50 = no signal, 1.0 = perfect.

**Post-outcome / leakage suspects (MUST DROP — known only during/after the build):**
| column | finding |
|---|---|
| `tr_log_status` | **STRONG LEAK.** fail-rate by value: broken 0.85, cancelled 1.00, ok 0.14, unknown 0.51. It is the build status parsed from the log. |
| `tr_log_num_tests_failed` | AUC 0.674; post-outcome test result. |
| `tr_log_bool_tests_failed` | post-outcome (all-null in sample). |
| `tr_duration`, `tr_log_buildduration`, `tr_log_testduration`, `tr_log_setup_time` | durations measured during/after the build. |
| `tr_log_num_tests_ok/failed/run/skipped`, `tr_log_num_test_suites_*`, `tr_log_tests_failed`, `tr_log_bool_tests_ran` | post-outcome test counts/lists. |
| `tr_log_lan`, `tr_log_analyzer`, `tr_log_frameworks` | derived by analyzing the build log → only exist after the build. (Spec's `tr_lan`/`tr_analyzer`/`tr_frameworks` map to these; **not used** — see deviation #4.) |

**Reassuring result — NO legitimate feature is a leak.** Among all 24 candidate features the
max symmetric AUC is **0.552** (`gh_repo_age`, `gh_repo_num_commits`); everything else is
0.50–0.55. No single pre-build feature predicts the target — consistent with the known
difficulty of build-failure prediction, and strong evidence the feature set is leakage-free.
Expect modest model AUC (~0.65–0.75 literature range), which is the honest target.

### Missingness (full file)
- **100% missing → DROP:** `gh_num_commits_in_push`.
- **~79% missing (PR-only fields), ~0.50 AUC → DROP:** `gh_num_issue_comments`,
  `gh_num_pr_comments`, `gh_description_complexity`.
- All kept features (`gh_*` sizes/diffs, `git_diff_*`, categoricals) are **0% missing**.
  Median imputation is still implemented per spec (defensive) but will rarely fire.

---

## FINAL LEAKAGE DROP LIST (floor = spec list, remapped to the real schema + extensions)

**Post-outcome (during/after build):** `tr_status` (target, never a feature),
`tr_duration`, `tr_log_status`, `tr_log_setup_time`, `tr_log_buildduration`,
`tr_log_testduration`, `tr_log_num_tests_ok`, `tr_log_num_tests_failed`,
`tr_log_num_tests_run`, `tr_log_num_tests_skipped`, `tr_log_num_test_suites_run`,
`tr_log_num_test_suites_ok`, `tr_log_num_test_suites_failed`, `tr_log_tests_failed`,
`tr_log_bool_tests_ran`, `tr_log_bool_tests_failed`, `tr_log_lan`, `tr_log_analyzer`,
`tr_log_frameworks`, `tr_jobs`, `tr_prev_build`, `tr_virtual_merged_into`.

**Identifiers / hashes / timestamps:** `tr_build_id` (kept only as dedup/group key, never in X),
`gh_project_name` (kept only as split-group key, never in X), `tr_job_id`, `tr_build_number`,
`git_commit`/`git_trigger_commit`, `git_merged_with`, `git_prev_built_commit`,
`tr_original_commit`, `git_all_built_commits` (giant hash list), `gh_commits_in_push`,
`git_branch`, `gh_pull_req_num`, `gh_pr_created_at`, `gh_first_commit_created_at`,
`gh_pushed_at`, `gh_build_started_at`.

**Dropped for missingness / no signal:** `gh_num_commits_in_push`, `gh_num_issue_comments`,
`gh_num_pr_comments`, `gh_description_complexity`.

---

## FINAL FEATURE SET (X) — all pre-build / known at trigger time (~26 features)

**Numeric (20):** `gh_team_size`, `git_num_all_built_commits`, `gh_num_commit_comments`,
`git_diff_src_churn`, `git_diff_test_churn`, `gh_diff_files_added`, `gh_diff_files_deleted`,
`gh_diff_files_modified`, `gh_diff_tests_added`, `gh_diff_tests_deleted`, `gh_diff_src_files`,
`gh_diff_doc_files`, `gh_diff_other_files`, `gh_num_commits_on_files_touched`, `gh_sloc`,
`gh_test_lines_per_kloc`, `gh_test_cases_per_kloc`, `gh_asserts_cases_per_kloc`,
`gh_repo_age`, `gh_repo_num_commits`.

**Categorical (label-encoded, mappings saved) (4):** `gh_lang`, `gh_is_pr`,
`gh_by_core_team_member`, `git_prev_commit_resolution_status`.

**Engineered (2):**
- `churn_ratio = git_diff_test_churn / (git_diff_src_churn + 1)`
- `test_coverage_proxy = gh_test_lines_per_kloc * gh_sloc / 1000`  (test-line density × code
  size ÷ 1000; an estimate of test volume, NOT a true coverage ratio).

A first-pass RF feature-importance review (Phase 3) may drop further low-value/redundant
features; any such drop will be justified and recorded here.

---

## CHOSEN CONFIGURATION (proposed — to confirm at checkpoint)

- **Unit:** build (dedup to one row per `tr_build_id`, keep first job row). ~925,896 builds.
- **Split:** **grouped by `gh_project_name`**, 70/15/15 train/val/test, `random_state=42`.
  Rationale: rows are successive builds of the same project, so a random split leaks project
  identity across train/test (verification test #3). A grouped split = no project on both
  sides = honest test of generalization to unseen projects, and the strictest leakage guard.
  Class ratio verified ≈ equal across splits (StratifiedGroupKFold used for CV folds).
- **Calibration subset:** carved from TRAIN only, grouped by project (~15% of train), held out
  from model fitting; used solely to fit Platt scaling. Never val, never test.
- **Model:** RandomForestClassifier, `criterion="gini"`, `class_weight="balanced"`,
  `random_state=42`, `n_jobs=-1`.
- **Tuning:** GridSearchCV, 5-fold StratifiedGroupKFold, `scoring = make_scorer(fbeta, beta=BETA)`.
  Search runs on a **stratified ~100k subsample** of train (dataset is large); final model is
  refit on the **full** train. Search space (proposed): `n_estimators [200,400]`,
  `max_depth [None,12,24]`, `min_samples_leaf [1,5,20]`, `max_features ["sqrt",0.5]`.
- **Calibration:** Platt scaling (LogisticRegression, no class_weight) on the calibration subset,
  minimizing binary cross-entropy.
- **Named constants (proposed):** `BETA = 2` (missed failure 2× costlier than false alarm),
  `r* = 0.80` (τ1 target recall), `p* = 0.70` (τ2 target precision).
- **Thresholds (1-D sweep on VALIDATION only):**
  - `τ1` = largest τ with `Recall(τ) ≥ r*` (PASS/WARN boundary).
  - `τ2` = smallest τ > τ1 with `Precision(τ) ≥ p*` (WARN/ROLLBACK boundary).
  - Enforce `τ1 < τ2`. **Fallbacks if a target is unreachable** (recorded in MEMORY.md):
    τ1 → median predicted prob; τ2 → 99th percentile of predicted prob (top-1% most confident).
- **Decision rule:** PASS if p < τ1; WARN if τ1 ≤ p < τ2; ROLLBACK if p ≥ τ2.
- **Explainability:** TreeSHAP (interventional), background = sample of passing builds (~200),
  explained on a test subsample.
- **Library versions (pinned in report):** numpy 2.5.0, pandas 3.0.3, scikit-learn / shap /
  joblib / matplotlib — **NOT yet installed; install in Phase 3 and pin actual versions.**

---

## DEVIATIONS / EXTENSIONS vs Chapter-3 (write back into the thesis)

1. **Schema remap.** Real columns differ from the spec reference; leakage list & features
   remapped to actual names (`tr_log_*`, `git_diff_*`, `gh_diff_*`, etc.).
2. **Unit = build, via dedup.** Spec assumed 1 row = 1 build; data is 1 row = 1 job
   (~4.19/build). Dedup to build level (status constant per build) — prevents a build's
   identical job-rows from straddling the split (row-level leakage) and from inflating metrics.
3. **Drop `started` builds** (outcome unknown) — 1 build.
4. **`tr_lan`/`tr_analyzer`/`tr_frameworks` NOT used as features.** They map to log-derived
   `tr_log_lan`/`tr_log_analyzer`/`tr_log_frameworks` = post-outcome. Only `gh_lang` (+ 3 other
   pre-build categoricals) is encoded. (Spec listed them as categoricals to encode.)
5. **Extra feature drops** for 79–100% missingness / ~0.50 AUC: `gh_num_commits_in_push`,
   `gh_num_issue_comments`, `gh_num_pr_comments`, `gh_description_complexity`.
6. **Split = grouped by project** (not plain stratified-random). Stratification preserved
   approximately via grouped split + ratio check / StratifiedGroupKFold.
7. **Calibration subset carved grouped within train.**
8. **Proposed policy constants** `r*=0.80`, `p*=0.70`, `BETA=2` + explicit fallback rules.
9. **Dataset ≈ 3.88M rows** (>> 1–2M estimate) → grid search on a subsample, final fit on full.

---

## PHASE-GROUPED CHECKLIST

### Phase 1 — Understand  ✅ (9/9)
- [x] Locate dataset, measure size, check installed libraries.
- [x] Read & verify real header (66 cols) vs spec reference; remap names.
- [x] Full-file row count, class balance, missingness (chunked, focused cols).
- [x] Confirm unit = job; count unique builds; verify status constant per build.
- [x] Sample across file; verify numeric coercibility / data quality.
- [x] Leakage scan (univariate AUC) — flag suspects; confirm no legit feature leaks.
- [x] Decide target definition + rows to drop.
- [x] Decide final leakage drop list + final feature set.
- [x] Write DATASET PROFILE + leakage-suspect list into PLAN.md.

### Phase 2 — Plan & propose  ⏳ (awaiting approval)
- [x] Write full plan, config, deviations into PLAN.md and MEMORY.md.
- [ ] **STOP — present profile + plan + deviations; get user approval before Phase 3.**

### Phase 3 — Implement (offline + inference)  ☐
- [ ] Git: `git init` + branch `thesis-pipeline` (repo is not yet a git repo).
- [ ] Install & pin scikit-learn, shap, matplotlib, joblib; write `requirements.txt`.
- [ ] Project layout: `src/`, `artifacts/`, `models/`, `tests/`, `config.py`.
- [ ] `config.py`: paths, column lists, BETA / r* / p*, split fractions, seeds, search space.
- [ ] Data loader: chunked read (usecols, na_values, downcast), dedup to build, target, drop list.
- [ ] Grouped split (train/val/test) + grouped calibration carve; persist split indices/ids.
- [ ] Preprocessing: label-encode (save mappings), median impute (train-only, saved),
      feature engineering (churn_ratio, test_coverage_proxy).
- [ ] RF + GridSearchCV (subsample, StratifiedGroupKFold, F-beta); log search & best params.
- [ ] Refit best RF on full train; first-pass importance review; optional feature pruning.
- [ ] Platt calibration on calibration subset.
- [ ] Threshold sweep on validation → τ1, τ2 (+ fallback handling).
- [ ] TreeSHAP (interventional) with passing-build background.
- [ ] Inference path: feature extraction → saved encoders/medians → RF → Platt → decision → SHAP → payload.
- [ ] Save all artifacts (model, calibrator, encoders, medians, thresholds, metadata).

### Phase 4 — Verify  ☐
- [ ] Tests 1–8 from <verification> as real automated tests; run until green
      (leakage tests #1–3 are blocking).

### Phase 5 — Artifacts  ☐
- [ ] Metrics (train/val/test): F1, Precision, Recall, ROC-AUC, PR-AUC, MCC, Brier.
- [ ] Threshold-sweep table, calibration curve, confusion matrix, SHAP/importance summary.
- [ ] Save all to `artifacts/`; write `LLM_PROMPT.md`.
- [ ] Final report with pinned versions; tick PLAN.md; record decisions in MEMORY.md.
