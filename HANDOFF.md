# HANDOFF.md — AI-in-CI/CD Build-Failure Prediction Pipeline

A complete, self-contained handoff. A reader with **no access to this codebase** should be able to (a) align thesis Chapter 3 (method/architecture) and Chapter 4 (results) with the implementation, and (b) defend the work to an examiner. Every number below is pulled from the on-disk artifacts; where a number is diagnostic-only or from a superseded run, the provenance is stated. Throughout, **FACT** = something measured from data (row counts, class balance, leakage-scan AUCs, the final metrics), **CHOICE** = a design or policy decision I made (e.g. BETA=2, r\*=0.80, p\*=0.70, the grouped-split decision, the leakage drop list, the alarm cutoffs, the fallback rules). These tags appear on section headings, bullets, and table captions; **a measured result and a chosen policy constant never carry the same kind of evidence**, and where a CHOICE is justified by a measurement, both are cited.

> **One-line summary:** A leakage-free Random Forest predicts, before a CI build finishes, the probability it will FAIL, and maps that probability to a three-state PASS / WARN / ROLLBACK decision. The honest cross-project test result is **ROC-AUC 0.860 / PR-AUC 0.749 / Brier 0.111**. The central scientific finding: ordinary diff-level features do **not** transfer across projects (cross-project ROC-AUC ≈ 0.515, near random); the predictive power comes from **leakage-free per-project prior-build history** features.

---

## 1. Problem & Framework

**What it predicts.** For a single CI build, using only information available **at trigger time** (before the build runs), the model outputs a calibrated probability `p` that the build will **fail**, where "fail" = the Travis status is anything other than `passed`.

**Target definition (CHOICE).** `y = 0` if `tr_status == "passed"`; `y = 1` for `failed`, `errored`, or `canceled`. Builds with `tr_status == "started"` (in-progress, outcome unknown) are dropped, as are rows with null `tr_status` or null build id.

**Three-state decision (CHOICE).** The calibrated probability is mapped to an operational action using two thresholds τ1 < τ2:

| condition | decision | meaning |
|---|---|---|
| `p < τ1` | **PASS** | low risk — let the build/deploy proceed |
| `τ1 ≤ p < τ2` | **WARN** | elevated risk — flag for attention (e.g. extra tests, review) |
| `p ≥ τ2` | **ROLLBACK** | high, confident risk — hold/stage the deploy behind a gate |

Thresholds are **operational-policy** choices selected on validation data (Section 7), **not** model hyperparameters and **not** tuned on test.

**Two-phase architecture (CHOICE, mirrors the thesis).**

- **Offline training pipeline** (`run_offline.py` + `bfp/`): load → dedup to build level → grouped split → fit preprocessing on train only → RF grid search on a subsample → refit on full train → Platt calibration on a held-out calibration subset → threshold selection on validation → TreeSHAP → write all artifacts.
- **Online inference path** (`bfp/inference.py`): raw build features → the **saved** preprocessor (same encoders/medians) → RF → Platt calibration → three-state decision → TreeSHAP attribution → structured payload (for the optional LLM layer).

---

## 2. Dataset Reality

**File (FACT).** `final-2017.csv`, **3.55 GB**, in the repo root. It is the canonical **TravisTorrent** schema with **66 columns** — this is the *real* header, which **differs from the schema assumed in the task brief**. The brief's reference header (with names like `tr_testduration`, `tr_setup_time`, `gh_src_churn`, a leading `row` index, etc.) was a hypothesis; the actual file uses `tr_log_*` prefixes for build-log-derived columns and `git_diff_*` / `gh_diff_*` for churn/diff columns. A name remapping was required (it drives the leakage list and feature list below).

**Schema: assumed vs real (selected, FACT).**

| brief assumed | real column | note |
|---|---|---|
| `row` (leading index) | *absent* | no leading index column |
| `tr_status` | `tr_status` | target (matches) |
| `tr_duration` | `tr_duration` | post-outcome |
| `tr_testduration`, `tr_purebuildduration`, `tr_setup_time` | `tr_log_testduration`, `tr_log_buildduration`, `tr_log_setup_time` | log-derived, post-outcome |
| `tr_tests_ok/fail/run/...` | `tr_log_num_tests_ok/failed/run/skipped`, `tr_log_num_test_suites_*` | log-derived, post-outcome |
| `gh_src_churn`, `gh_test_churn` | `git_diff_src_churn`, `git_diff_test_churn` | pre-build diff metrics |
| `gh_files_added/...` | `gh_diff_files_added/deleted/modified` | pre-build diff metrics |
| `tr_lan`, `tr_analyzer`, `tr_frameworks` | `tr_log_lan`, `tr_log_analyzer`, `tr_log_frameworks` | **log-derived ⇒ post-outcome, excluded** |
| (n/a) | `tr_log_status` | **strong leak**, see Section 4 |

**Row count and the job-vs-build discovery (FACT).** The file has **3,881,992 rows**, far above the brief's ~1–2M estimate. Crucially, **each row is one Travis _job_, not one _build_**. A build expands to multiple job rows (~**4.19 jobs/build** on average). In the head sample, build `3154` appears as 4 rows differing only in `tr_job_id` / `tr_log_*` / `tr_duration`; all `gh_*` and `git_diff_*` feature values are identical across a build's jobs.

**Unique builds (FACT).** **925,897** unique builds. Build status is **constant within every build** (measured: 0 builds had inconsistent status across their jobs), which makes deduplication to build level safe (Section 3). After dropping the 1 `started` build, the modeled set is **925,896 builds**.

**Class balance / failure rate (FACT, build-level after dedup).**

| status | builds | share |
|---|---|---|
| passed | 691,164 | 74.65% |
| failed | 167,204 | 18.06% |
| errored | 64,256 | 6.94% |
| canceled | 3,272 | 0.35% |
| started | 1 | dropped |

→ **Failure rate (y=1) = 0.2535** (234,732 failures / 925,896 builds). No extreme imbalance.

**Projects & languages (FACT).** **948 unique projects** (`gh_project_name`). Languages present: **go, java, python, ruby**. (Measured failure rate by language on the profiling sample: go ≈ 0.19, java ≈ 0.29, python ≈ 0.27, ruby ≈ 0.29.)

**Missingness (full file).** *The missing percentages are **FACT** (measured over the whole file); the keep/drop **decision** column and the chosen drop cutoff (drop if ~79–100% missing and ≈0.50 AUC) are **CHOICEs**.*

| column(s) | missing (FACT) | decision (CHOICE) |
|---|---|---|
| `gh_num_commits_in_push` | 100% | dropped (useless) |
| `gh_num_issue_comments`, `gh_num_pr_comments`, `gh_description_complexity` | ~79% (PR-only fields) and ≈0.50 AUC | dropped (no signal) |
| all kept `gh_*` sizes/diffs, `git_diff_*`, the 4 categoricals | 0% | kept |
| `tr_build_number` (ordering key) | 0% | used for history ordering only |

All profiled numeric columns coerce cleanly (0 non-coercible non-null values). Missing tokens are `NA` and `""`. Median imputation is implemented per the method but, given 0% missingness in the kept raw features, it rarely fires (it does fill the first-build NaNs of the history features — Section 5).

---

## 3. Unit of Analysis — the Build

**CHOICE.** The unit is a **build**, obtained by deduplicating job rows to one row per `(gh_project_name, tr_build_id)` (keeping the first job row). The loader does this memory-safely: job rows of a build are contiguous, so consecutive-duplicate build ids are collapsed while streaming the 3.9M rows in chunks, then a final `drop_duplicates` guarantees correctness for any non-contiguous repeats.

**Why dedup is required (and what breaks without it):**

1. **Row-level leakage / split contamination.** The features are build-level (identical across a build's jobs). Without dedup, the ~4 job rows of one build would be scattered across train/val/test, putting near-identical rows on both sides of the split — a textbook leak that inflates metrics.
2. **Metric inflation & mis-weighting.** Builds with more jobs would count ~4× more, biasing both training and evaluation toward high-job-count builds.
3. **Target consistency.** Verified that status is constant within a build, so collapsing to one row loses no label information.

---

## 4. Data Leakage — the Centerpiece

Leakage was treated as the top priority, overriding accuracy. Two forms were guarded.

### 4a. Column-level leakage (post-outcome values and identifiers)

Every column whose value is known **only during or after** the build, plus every identifier/hash/timestamp, is excluded from the feature matrix `X`. **Classifying a column as post-outcome and dropping it is a design CHOICE grounded in domain reasoning about *when* each value becomes known — it is not itself a measurement.** The one piece of *measured* leak evidence in this subsection is the `tr_log_status` scan (FACT) called out below. The full drop list (the brief's floor, remapped to the real schema, plus extensions):

**Post-outcome (known only during/after the build):**

| column | why dropped |
|---|---|
| `tr_status` | the target itself — never a feature |
| **`tr_log_status`** | **the strong leak that was caught** — the build's status parsed from the log (see below) |
| `tr_duration`, `tr_log_buildduration`, `tr_log_testduration`, `tr_log_setup_time` | durations measured during/after the build |
| `tr_log_num_tests_ok/failed/run/skipped`, `tr_log_num_test_suites_run/ok/failed`, `tr_log_tests_failed` | test counts/lists produced by running the build |
| `tr_log_bool_tests_ran`, `tr_log_bool_tests_failed` | booleans set after the build runs |
| `tr_log_lan`, `tr_log_analyzer`, `tr_log_frameworks` | derived by analyzing the build log ⇒ exist only after the build (these are the real-schema counterparts of the brief's `tr_lan`/`tr_analyzer`/`tr_frameworks`) |
| `tr_jobs`, `tr_prev_build`, `tr_virtual_merged_into` | post/ambiguous identifiers tied to build execution |

**Identifiers / hashes / timestamps (carry no legitimate signal, or are keys):**
`tr_build_id` (kept **only** as dedup key, never in `X`), `gh_project_name` (kept **only** as the split-group key, never in `X`), `tr_job_id`, `tr_build_number` (kept **only** to order builds for history, never in `X`), `git_trigger_commit`, `git_merged_with`, `git_prev_built_commit`, `tr_original_commit`, `git_all_built_commits` (a giant per-row hash list), `gh_commits_in_push`, `git_branch`, `gh_pull_req_num`, `gh_pr_created_at`, `gh_first_commit_created_at`, `gh_pushed_at`, `gh_build_started_at`.

**Dropped for missingness / no signal:** `gh_num_commits_in_push`, `gh_num_issue_comments`, `gh_num_pr_comments`, `gh_description_complexity`.

**The strong leak that was caught — `tr_log_status` (FACT).** On a 116,460-row stratified sample, the failure rate conditioned on `tr_log_status` was: `broken` 0.85, `cancelled` 1.00, `ok` 0.14, `timeout` 0.69, `unknown` 0.51. It is effectively the outcome re-encoded. Had it (or any `tr_log_*` test result) been left in `X`, the model would have achieved near-perfect, **meaningless** scores — a classic "predict the outcome from the outcome" leak. It is on the drop list and is caught by the automated tests below.

### 4b. Row-level leakage (project identity across the split)

**CHOICE: grouped-by-project split.** Because rows are successive builds of the **same project**, a naïve random split places builds of one project on both sides of train/test. The model then "recognizes" the project rather than learning a generalizable rule — project identity leaks across the split. To prevent this, the split is **grouped by `gh_project_name`** (via `GroupShuffleSplit`, seed 42), so **no project appears on two sides**. The same grouping is applied when carving the calibration subset from train, and CV folds use `StratifiedGroupKFold`.

This is the strictest, most honest setup: the test set measures generalization to **entirely unseen projects**. Its cost is that exact class-ratio stratification is impossible under grouping; ratios are reported and verified close (Section 7 / split table).

The damage a random split would do is quantified directly in the **ablation table (Section 8)**: the same features/model jump from ROC-AUC ≈ 0.515 (grouped) to ≈ 0.845 (random) — that 0.845 is **project-identity leakage and must not be reported as a result.**

### 4c. Univariate leakage scan (FACT)

On the 116,460-row stratified sample, each candidate feature's univariate symmetric AUC against the target (`max(auc, 1-auc)`; 0.50 = no signal) was measured. **No legitimate pre-build feature exceeds ≈ 0.552** (`gh_repo_age`, `gh_repo_num_commits`); everything else is 0.50–0.55. This is reassuring two ways: (1) no single pre-build feature is secretly the outcome, and (2) it foreshadows that diff-level features are individually weak — consistent with the known difficulty of build-failure prediction.

### 4d. Automated leakage tests (guards)

Implemented as real `pytest` tests; all pass. The three leakage tests are treated as blocking.

| # | test | asserts |
|---|---|---|
| 1 | column-level | no drop-list column is in `X`; `tr_status`/`y` not derivable; `X.columns == FEATURE_ORDER` exactly |
| 2 | signal-level | test ROC-AUC `< 0.99` **and** max single-feature importance `< 0.50`; trips (fails) and names the offender otherwise |
| 3 | row-level | no project shared across train/val/test |
| 9 | temporal (history) | history features recomputed with a shift match the stored columns; ordering keys never reach `X`; first build of each project has NaN prior status |

(Tests 4–8 cover train/inference consistency, no-test-contamination, reproducibility, threshold ordering/targets, and an end-to-end smoke run — Sections 7, 10.)

**The alarm cutoffs (test #2: ROC-AUC ≥ 0.99, importance ≥ 0.50) are CHOICEs** — deliberately chosen suspicion thresholds, *not* data-derived values. Their job is to fail the build loudly if leakage ever inflates a result; that the final model passes them (0.860 < 0.99, 0.281 < 0.50) is the FACT (Section 8).

**Test scope (important — what "9 tests pass" does and does not mean).** The suite runs via `tests/conftest.py`, which builds one small end-to-end pipeline on a **250,000-job-row prefix** of the CSV (tens of thousands of builds spanning many projects, since projects are interleaved), with a deliberately tiny **single-point quick grid** (`n_estimators=120, max_depth=12, min_samples_leaf=10, max_features="sqrt"`) and an **8,000-row** tuning subsample. This is fast yet exercises the full grouped-split → tune → calibrate → threshold → SHAP → inference path. The tests therefore verify the **pipeline's logic and safety** — no column/row/temporal leakage, train-vs-inference consistency, no-test-contamination, deterministic reproducibility, threshold ordering — and **not** the full-data performance. The headline metrics in Section 8 (ROC-AUC 0.860, etc.) come from the **full 925,896-build run** produced by `run_offline.py`, *not* from the test fixture. In short: "9 tests pass" means "the method is leakage-free and internally consistent," **not** "0.860 is re-verified by the tests."

---

## 5. Features

The feature matrix `X` is **32 columns**, all pre-build / known at trigger time.

> **FACT vs CHOICE for this section:** *which* columns are kept (5a), the two engineered formulas (5b), the drops (5c), and the history-feature definitions/windows (5d) are all design **CHOICEs**. The measurements that justify them — missingness, univariate AUC (Section 4c), the ordering/shift checks (5d), and the importances (Section 8) — are **FACTs**, cited alongside.

### 5a. Raw features kept

**Numeric (20):** `gh_team_size`, `git_num_all_built_commits`, `gh_num_commit_comments`, `git_diff_src_churn`, `git_diff_test_churn`, `gh_diff_files_added`, `gh_diff_files_deleted`, `gh_diff_files_modified`, `gh_diff_tests_added`, `gh_diff_tests_deleted`, `gh_diff_src_files`, `gh_diff_doc_files`, `gh_diff_other_files`, `gh_num_commits_on_files_touched`, `gh_sloc`, `gh_test_lines_per_kloc`, `gh_test_cases_per_kloc`, `gh_asserts_cases_per_kloc`, `gh_repo_age`, `gh_repo_num_commits`.

**Categorical (4, label-encoded; maps saved; unseen/missing → −1):** `gh_lang`, `gh_is_pr`, `gh_by_core_team_member`, `git_prev_commit_resolution_status`.

### 5b. Engineered features (2) — formulas

- **`churn_ratio` = `git_diff_test_churn / (git_diff_src_churn + 1.0)`** — test churn relative to source churn (the `+1` avoids divide-by-zero). Intuition: are tests being updated alongside source?
- **`test_coverage_proxy` = `gh_test_lines_per_kloc * gh_sloc / 1000.0`** — test-line density × code size ÷ 1000; an estimate of **test volume** relative to code size. **Not** a true coverage ratio (named "proxy" deliberately). Infinities from the ratio are tamed to NaN then median-imputed.

### 5c. Features dropped for missingness / no signal

`gh_num_commits_in_push` (100% missing), `gh_num_issue_comments`, `gh_num_pr_comments`, `gh_description_complexity` (~79% missing, ≈0.50 AUC). See Section 2.

### 5d. History features (6) — the key extension

These supply the **transferable** signal. Each is computed **per project, from that build's own strictly-prior builds only.**

| feature | definition (per project, strictly prior to the current build) |
|---|---|
| `hist_prev_status` | outcome (0/1) of the immediately previous build |
| `hist_fail_rate_5` | mean failure over the previous 5 builds |
| `hist_fail_rate_20` | mean failure over the previous 20 builds |
| `hist_fail_rate_all` | expanding mean failure over **all** previous builds |
| `hist_consec_fail` | length of the trailing run of consecutive prior failures |
| `hist_build_seq` | number of prior builds of this project (experience/age in builds) |

**Exactly how they are computed.** Builds are sorted within each project by `tr_build_number` (the Travis per-project build counter), with `tr_build_id` as a tiebreak. All statistics are computed on the target series **shifted by one** (`groupby(project)['y'].shift(1)` and rolling/expanding aggregations of the shifted series), so **the current build's own outcome is never part of its own feature**. The first build of a project therefore has NaN history (median-imputed downstream); `hist_build_seq` is 0 there. `tr_build_number` is used purely for ordering and is **dropped from `X`** (it is on the leakage list).

**Why these are NOT leakage (the explicit argument).** At the moment build *N* of a project is triggered, the outcomes of builds 1…*N*−1 of that **same project** are already known — they are historical fact available before build *N* runs. Using them is exactly what a real deployed system would do. The shift-by-one guarantees no use of the present or future. Three independent checks confirm it:

- **Ordering is unambiguous (FACT):** `tr_build_number` is 0% missing, and per-project Spearman correlation between `tr_build_number` and `tr_build_id` is **1.000 for all projects** — both agree on chronological order.
- **Shift is correct (FACT):** `hist_prev_status` matches an independent manual shift-by-1 exactly, and the first build per project is NaN.
- **Strength is plausible, not perfect:** the resulting model AUC is 0.860, not ≈1.0 — consistent with strong-but-imperfect past signal, not an outcome leak.
- **Guarded forever:** automated **test #9** re-derives the shifted statistics and fails if any history column accidentally includes the current build.

> **Caveat on the history computation (honest).** The history features are computed on the **full** build table before splitting. Under the **grouped** split this is clean: a project lives entirely on one side, so a row's history never draws on the other side's rows. If the split strategy were ever changed to random/within-project, the history computation would need to be recomputed per-split (train-only history) to stay clean. With the current grouped split there is no contamination.

---

## 6. Model & Tuning

**Model (CHOICE).** `RandomForestClassifier` with fixed `criterion="gini"`, `class_weight="balanced"`, `random_state=42`, `n_jobs=-1`.

**Grid search (CHOICE/method).** `GridSearchCV` with **5-fold `StratifiedGroupKFold`** (grouped by project so CV folds don't leak project identity either), scoring = **F-beta with BETA = 2** (`make_scorer(fbeta_score, beta=2, pos_label=1)`). BETA = 2 encodes that a **missed failure is ~2× costlier than a false alarm** (recall-favoring). The search runs on a **stratified 80,000-row subsample** of `train_fit` (the data is large); the **final model is refit on the full `train_fit`** with the winning params.

**Full search space (CHOICE — the ranges and the 80,000-row subsample size are design decisions; 24 candidates = 2×2×3×2):**

| hyperparameter | values |
|---|---|
| `n_estimators` | 200, 400 |
| `max_depth` | None, 16 |
| `min_samples_leaf` | 1, 5, 20 |
| `max_features` | "sqrt", 0.4 |

**Chosen best (FACT).** `{max_depth: 16, max_features: 0.4, min_samples_leaf: 20, n_estimators: 400}`, **CV F-beta = 0.7328** (subsample = 80,000, StratifiedGroupKFold(5)). The **full per-candidate CV table** (all 24, with mean/std test score and rank) is saved at **`artifacts/grid_search.json`**.

**What the CV table shows (FACT, defensible insight).** The dominant factor is `min_samples_leaf`: the **top 8 candidates all use `min_samples_leaf=20`** (scores 0.7305–0.7328), while every `min_samples_leaf=1` candidate is worst (the bottom 8, down to 0.6893) — i.e. unconstrained leaves overfit on this noisy target. `max_features=0.4` edges out `"sqrt"`, and `n_estimators`/`max_depth` matter little. The whole top group is within ~0.002 F-beta, so the choice is robust.

---

## 7. Calibration & Thresholds

**Calibration (CHOICE/method).** **Platt scaling** — a `LogisticRegression` (near-unregularized, `C=1e6`, **no class weight**, fit by binary cross-entropy) mapping the RF positive-class probability to a calibrated probability. It is fit on a **dedicated calibration subset carved (grouped) from TRAIN only** — never validation, never test. (Split sizes below.)

**Threshold policy (CHOICE — operational, not data-optimized).** Two thresholds are selected on the **validation set only** (never test), using target-based criteria so the policy is coherent with the recall-favoring model. Mechanically, the candidate thresholds are the distinct cut-points of the **validation precision–recall curve** (`sklearn.metrics.precision_recall_curve`), scanned for the two conditions below — *not* a fixed uniform grid. (Separately, a uniform 1001-step 0→1 grid — `THRESH_GRID_STEPS` — is evaluated **only** to produce the reported `threshold_sweep_val.csv` and the sweep plot; it is **not** used to choose τ1/τ2.) The criteria:

- **τ1 (PASS/WARN)** = the **largest** τ such that `Recall(τ) ≥ r*`, with **r\* = 0.80**. Guarantees WARN+ROLLBACK catch ≥80% of real failures.
- **τ2 (WARN/ROLLBACK)** = the **smallest** τ > τ1 such that `Precision(τ) ≥ p*`, with **p\* = 0.70**. Makes ROLLBACK fire only when the model is confidently right.

`r*`, `p*`, and BETA are **policy constants** reflecting the cost of misclassification; they are **not** fit to data. F1 and MCC are computed and reported but are **not** used to choose thresholds.

**Fallback rules (CHOICE).** If no τ meets a target: τ1 → median predicted probability; τ2 → 99th percentile of predicted probability; and τ1 < τ2 is force-enforced. Any fallback is recorded.

**Final thresholds (FACT).** **τ1 = 0.1119, τ2 = 0.4662.** τ1 < τ2 holds. **No fallback fired** (`{tau1: false, tau2: false}`). On validation, `Recall@τ1 = 0.8000` (exactly hits r*=0.80) and `Precision@τ2 = 0.7000` (exactly hits p*=0.70).

> **Honest note on fallback risk.** Because both targets are met *exactly* at the boundary on validation, the policy sits right at the edge of its feasible region — a slightly higher r* or p* could have forced a fallback. This is recorded so the examiner sees the constants are demanding but satisfiable. Test #7 asserts τ1<τ2 and that each target is met (or a fallback is recorded).

**Split sizes (FACT, full data, seed 42, grouped):**

| split | builds | projects | failure_rate |
|---|---|---|---|
| train | 663,911 | 662 | 0.2640 |
| ├ train_fit | 540,695 | 562 | 0.2794 |
| └ calib | 123,216 | 100 | 0.1967 |
| val | 123,316 | 143 | 0.2120 |
| test | 138,669 | 143 | 0.2401 |

948 projects total; no project on two sides. Class ratios vary 0.20–0.28 — the unavoidable cost of moving whole projects together; reported and accepted.

---

## 8. Results — Honest Numbers

All numbers below are from the **current** `artifacts/` (final model: grouped/cross-project, diff + history). Per-split metrics; threshold-based columns are evaluated at τ1.

**Evaluation protocol & row budget (FACT — what saw what).** The final run used **all 925,896 builds**, split grouped by project. Each downstream stage saw a strictly smaller, disjoint slice, and **the test set was used exactly once, at the end**:

| stage | data used | builds | touched test? |
|---|---|---|---|
| grid search (24 candidates, 120 fits) | stratified **subsample** of train_fit | 80,000 | no |
| RF refit (final model) | full train_fit | 540,695 | no |
| Platt calibration | calib subset (carved from train) | 123,216 | no |
| threshold selection (τ1=0.1119, τ2=0.4662) | **validation only** | 123,316 | no |
| **final evaluation @ chosen τ1/τ2** | **held-out test (unseen projects)** | **138,669** | **applied once** |

So the **chosen thresholds were tested on 138,669 builds** — the entire test split. Threshold-free metrics (ROC-AUC, PR-AUC, Brier) are computed on all 138,669; the τ-based metrics (precision/recall/F1/MCC, 3-state confusion) use the same 138,669 with decisions made at τ1/τ2. **No test row entered tuning, calibration, or threshold choice** (guarded by no-test-contamination test #5).

**Full metrics table (FACT, `artifacts/metrics.json`):**

| split | ROC-AUC | PR-AUC | Brier | Precision@τ1 | Recall@τ1 | F1@τ1 | MCC@τ1 | TP/FP/FN/TN |
|---|---|---|---|---|---|---|---|---|
| train | 0.9225 | 0.8621 | 0.0940 | 0.5522 | 0.9163 | 0.6892 | 0.5653 | 138423/112230/12637/277405 |
| val | 0.8477 | 0.6902 | 0.1092 | 0.4342 | 0.8000 | 0.5629 | 0.4353 | 20911/27247/5227/69931 |
| **test** | **0.8602** | **0.7489** | **0.1105** | **0.4747** | **0.8220** | **0.6019** | **0.4634** | 27367/30279/5926/75097 |

- **Test base rate (FACT):** 0.2401. CV F-beta of the chosen model: **0.7328**.
- **Leakage alarms (FACT):** test ROC-AUC 0.8602 < 0.99 ✓; max single-feature importance 0.2808 < 0.50 ✓. Neither tripped.

**Three-state decision confusion — test (FACT, actual × decision):**

| actual \ decision | PASS | WARN | ROLLBACK |
|---|---|---|---|
| pass (n=105,376) | 75,097 | 23,084 | 7,195 |
| fail (n=33,293) | 5,926 | 7,554 | 19,813 |

Derived operating characteristics (FACT):
- **ROLLBACK precision** = 19,813 / (19,813 + 7,195) = **0.7336** (consistent with p*=0.70 target).
- **Failures flagged** (WARN+ROLLBACK) = (7,554 + 19,813) / 33,293 = **82.2%** of all real failures (equals Recall@τ1).
- **Missed failures** (failures sent to PASS) = 5,926 / 33,293 = **17.8%**; as a share of all PASS decisions = 5,926 / 81,023 = **7.3%** false-pass rate.

**Top features — RF importance (FACT, `artifacts/feature_importances.json`):**

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

**Top features — mean |TreeSHAP| (FACT, interventional, 500-row test sample, `artifacts/shap_summary.json`):** hist_consec_fail 0.0670, hist_prev_status 0.0559, hist_fail_rate_20 0.0396, hist_fail_rate_5 0.0367, hist_fail_rate_all 0.0351, then `git_prev_commit_resolution_status` 0.0147, `git_num_all_built_commits` 0.0120, `gh_diff_other_files` 0.0104. The five history features dominate both rankings; diff-level features contribute weakly but non-trivially.

### 8a. Ablation table (mandatory) — what the split and history do

| configuration (test) | split | ROC-AUC | PR-AUC | Brier | provenance |
|---|---|---|---|---|---|
| diff features only | grouped (cross-project) | **0.515** | 0.252 | 0.189 | first full run, commit `9bdf68c`; metrics.json since overwritten — reproducible via `USE_HISTORY=False` |
| diff features only | **random** (within-project) | **0.845** | 0.749 | not recorded | diagnostic script (`scratchpad/diag_split.py`); **NOT a result — project-identity leakage** |
| **diff + history** (final) | grouped (cross-project) | **0.860** | **0.749** | **0.111** | current `artifacts/metrics.json` |

Supporting subsample diagnostics (≈305k builds, same features/model; provenance = diagnostic scripts, not saved artifacts): grouped diff-only **0.559**, random diff-only **0.845**, grouped **+history 0.894**.

**What this proves.**
1. **No column leakage.** With diff features only, once projects are held out (grouped), the model is **near random (0.515)**. If a post-outcome column had survived into `X`, this number would be high. Its near-randomness is positive evidence the feature set is clean.
2. **Random splits are deceptive.** The *same* features/model score **0.845** under a random split purely because projects appear on both sides — the model memorizes project identity. This 0.845 is the kind of inflated number naïve TravisTorrent setups report; here it is explicitly labeled as leakage and **excluded from the results**.
3. **History is the transferable signal.** Adding leakage-free per-project prior-build history lifts the **honest, grouped** result from 0.515 to **0.860** — and does so without reintroducing leakage (alarms clean, ordering exact, test #9 green). The story is "recently-failing projects keep failing," a rule that generalizes across unseen projects, unlike raw project identity.

---

## 9. Failures & Dead Ends (candid)

- **The near-random first result.** The first full pipeline (diff features only, grouped split) produced test **ROC-AUC ≈ 0.515**. Rather than treat it as a bug, it was investigated: a controlled diagnostic (same features/model, random vs grouped split) showed random-split = 0.845 vs grouped = 0.559. Conclusion: the pipeline is correct; **diff-level features simply don't transfer across projects.** This drove the history-feature extension and became the thesis's central methodological finding.
- **Session teardowns during refit.** Two long background runs were killed by environment/session teardown **after** grid search but **before** artifacts were saved, wasting ~15 minutes of search each time. Fix: the grid result is now **checkpointed to `artifacts/grid_search.json`** immediately after the search, and `run_offline.py` accepts **`--resume-grid`** to reuse it and finalize quickly. A teardown can no longer waste the search.
- **Trimmed-then-full grid.** To get a run to complete under interruption pressure, the grid was temporarily trimmed to 8 candidates (`max_features` fixed to "sqrt"). Best params then: `max_features=sqrt, depth16, leaf20, 400` (test ROC-AUC 0.8601). The **full 24-candidate** grid was later run for defensibility; it chose `max_features=0.4` and produced test ROC-AUC **0.8602** — i.e. **trimming changed nothing material** (Δ ≈ 0.0001). Both are documented; the full grid is the reported configuration.
- **Threshold targets at the boundary.** As noted in Section 7, r*=0.80 and p*=0.70 are met *exactly* on validation — the policy is feasible but sits at the edge; slightly stricter targets would have triggered the documented fallbacks.
- **Reproducibility nuance (not a failure, documented).** With `n_jobs=-1`, parallel tree aggregation introduces sub-ULP (~1e-16) nondeterminism in probabilities. The reproducibility test asserts predictions are equal to `atol=1e-9` and ROC-AUC equal to 9 decimals — i.e. scientifically identical; bit-exactness is not claimed.

---

## 10. Reproducibility

**Determinism (CHOICE).** `random_state = 42` everywhere (split, RF, subsampling, SHAP sampling). Splits reproduce exactly by build id (test #6); the refit RF reproduces predictions to `atol=1e-9` and identical ROC-AUC to 9 decimals.

**Library versions.** The versions that actually produced the artifacts are **recorded at runtime** in `artifacts/metadata.json` and `REPORT.md`: python 3.12.10, **numpy 2.4.6**, pandas 3.0.3, scikit-learn 1.9.0, shap 0.52.0, joblib 1.5.3. `requirements.txt` is pinned to match these (numpy==2.4.6, pandas==3.0.3, scikit-learn==1.9.0, shap==0.52.0, matplotlib==3.11.0, joblib==1.5.3, pytest>=8.0).

> *History note:* `requirements.txt` originally mis-pinned numpy as 2.5.0 while the run used 2.4.6; this was corrected to 2.4.6 so the pin matches the recorded run.

**Saved on disk.**

| path | contents |
|---|---|
| `models/preprocessor.joblib` | fitted `Preprocessor`: **label-encoder maps** (`cat_maps_`) and **train medians** (`medians_`) and the feature order |
| `models/rf_model.joblib` | the refit Random Forest |
| `models/calibrator.joblib` | the Platt `LogisticRegression` calibrator |
| `models/thresholds.json` | `tau1`, `tau2`, `r_star`, `p_star`, fallback flags, recall@τ1, precision@τ2 |
| `models/feature_order.json` | exact column order of `X` |
| `models/shap_background.npy` | passing-build background set for TreeSHAP at inference |
| `artifacts/metrics.json` | train/val/test: ROC-AUC, PR-AUC, Brier, precision/recall/F1/MCC@τ1, confusion, calibration-curve bins |
| `artifacts/grid_search.json` | best params + **full 24-candidate CV table** |
| `artifacts/feature_importances.json`, `artifacts/shap_summary.json` | RF importances; mean |SHAP| |
| `artifacts/threshold_sweep_val.csv` | precision/recall/F1 across thresholds on validation |
| `artifacts/metadata.json` | versions, seed, split report, leakage drop list, feature order, search summary, constants, thresholds, alarms |
| `artifacts/*.png` | calibration curve, threshold sweep, feature importance, SHAP summary, 3-state confusion |
| `REPORT.md` | auto-generated Chapter-4 results (regenerate with `python make_report.py`) |

**How to re-run.**
1. `pip install -r requirements.txt` (numpy 2.4.6, matching the recorded run — see above).
2. Place `final-2017.csv` in the repo root.
3. `python run_offline.py` (full run; ~11–18 min: ~15 min for the 120-fit grid + refit + SHAP). Use `--resume-grid` to skip re-searching if `artifacts/grid_search.json` exists; `--max-rows N --quick` for a fast smoke run.
4. `python make_report.py` to regenerate `REPORT.md`.
5. `pytest -q` to run all 9 verification tests.

**Inference consistency (test #4, FACT).** The inference path loads the **saved** preprocessor/model/calibrator/thresholds (not fresh ones); the test asserts the loaded medians/maps equal the fitted ones (and are not zeros), that loaded-vs-fitted transforms are identical, and that `InferencePipeline.predict` reproduces the manual probability path to `<1e-9`.

---

## 11. LLM Analysis Layer

**Architecture-only; not implemented.** No LLM is called anywhere in the pipeline. The offline/inference code produces a structured `report_payload` per build — `{decision, failure_probability, thresholds, top_features:[{feature, value, shap}]}` — and **`LLM_PROMPT.md`** contains a ready-to-use prompt template that turns that payload into a short human-readable report with exactly three sections: **Likely cause**, **Contributing factors** (using the SHAP sign convention: positive SHAP → raises failure risk), and **Remediation suggestions**. The template constrains the model to use **only** the provided per-build data (no invented logs/tests/stack traces), keeping the analysis auditable and reproducible. The LLM model/API is a **clearly marked TODO** (suggested default: latest Claude via the Anthropic API, temperature ~0.2). Because the layer is explanation-only and never changes the decision, it is freely replaceable.

---

## 12. Thesis Mapping (Chapter 3 vs Chapter 4)

Each significant decision and where it belongs. **DEVIATION/EXTENSION** marks items that differ from or extend a typical Chapter-3 description and should be written back into the text (these consolidate PLAN.md/MEMORY.md deviations #1–#10 plus the history-features and ablation items).

| topic | Ch. 3 (method) | Ch. 4 (results) | deviation/extension? |
|---|---|---|---|
| Target definition (`passed`=0 else 1; drop `started`) | yes | — | minor: explicit `started` drop |
| Two-phase offline/online architecture | yes | — | — |
| **Schema remap** (real TravisTorrent vs assumed header) | yes (data description) | — | **DEVIATION #1** |
| **Unit = build via dedup** (rows are jobs, ~4.19/build) | yes (data prep) | dataset stats | **DEVIATION #2** |
| Leakage drop list (post-outcome + ids) incl. `tr_log_status` | yes | — | extends floor; `tr_lan/analyzer/frameworks` excluded = **DEVIATION #4** |
| **Row-level: grouped-by-project split** | yes (validation design) | split table | **DEVIATION #6** |
| Grouped calibration subset carved from train | yes | — | **DEVIATION #7** |
| Extra feature drops (missingness/no-signal) | yes | missingness table | **DEVIATION #5** |
| Engineered `churn_ratio`, `test_coverage_proxy` | yes (formulas) | importance/SHAP | proxy naming clarified |
| **History features (6, strictly-prior, shift-1)** | yes (feature method + leakage argument) | importance/SHAP, ablation | **EXTENSION #10 — central** |
| RF config + F-beta(BETA=2) grid, StratifiedGroupKFold, subsample+refit | yes | chosen params, CV table | subsample+refit = **DEVIATION #9** |
| Platt calibration (no class weight) | yes | calibration curve, Brier | — |
| Threshold policy (τ1=r\*, τ2=p\*), fallbacks, constants r\*=0.80/p\*=0.70/BETA=2 | yes | final τ values, confusion | **DEVIATION #8** (constants + fallbacks) |
| TreeSHAP (interventional, passing-build background) | yes | SHAP summary | — |
| Univariate leakage scan (max AUC ≈0.552) | yes (leakage analysis) | scan finding | extension |
| **Ablation: grouped vs random, ±history** | method note | **ablation table — key result** | **EXTENSION — central** |
| Leakage alarms (ROC-AUC<0.99, importance<0.50) + 9 tests | yes (validation) | alarm check | extension |
| LLM analysis layer | yes (architecture, prompt) | — | not implemented (by design) |

---

## 13. Limitations & Future Work

**Limitations (honest).**
- **Cross-project prediction is intrinsically hard.** With diff-level features only, unseen-project performance is near random (0.515). The usable signal is dominated by a project's **own** recent failure history; for a **brand-new project with no history**, the model falls back to weak diff-level features (the history columns are median-imputed) and should be expected to perform near that 0.515 floor until the project accumulates builds.
- **Modest ceiling, history-dependent.** The 0.860 result leans heavily on `hist_consec_fail` / `hist_prev_status` (importance 0.28 / 0.26). This is legitimate but means the model is, in large part, an "autocorrelation of failure" detector; the non-history features add little.
- **Policy-constant sensitivity.** r*=0.80 and p*=0.70 are met *exactly* at the validation boundary; small changes could trigger fallbacks and shift τ1/τ2 materially. The PASS bucket still misses 17.8% of failures (7.3% false-pass), inherent to a recall-0.80 policy.
- **Calibration in the tails.** Brier is good (0.111) and the curve is monotonic, but high-probability bins are sparse; ROLLBACK precision (0.734) rests on relatively few builds.
- **Single dataset / era.** TravisTorrent `final-2017.csv`, 4 languages, 948 projects. Generalization to other CI systems (GitHub Actions, GitLab CI) or later years is untested.
- **History computed pre-split** — clean under the grouped split only (see Section 5d caveat).

**Future work (reasonable).**
- Add a **per-project temporal (forward-chaining) split** as a second operating scenario (train on a project's past builds, test on its future builds) — the most deployment-faithful evaluation; report it alongside the grouped (cross-project) result.
- **Cold-start handling:** a separate model or prior for projects with little/no history; a missing-history indicator feature.
- Richer leakage-free history (time since last build, author-level failure history, rolling churn trends).
- Compare RF against gradient-boosted trees (XGBoost/LightGBM) under the identical leakage controls.
- Implement and evaluate the **LLM analysis layer** against the template; measure usefulness of remediation suggestions.
- Sensitivity analysis sweeping BETA / r* / p* to map the PASS/WARN/ROLLBACK operating frontier for the thesis.

---

*End of HANDOFF.md — self-contained as of the final full 24-candidate grid run (seed 42).*
