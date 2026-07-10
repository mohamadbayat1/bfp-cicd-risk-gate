# Chapter 4 — artifact tracker

Generated tables/figures for Chapter 4. Every file here is produced by a script in
`scripts/` from either an existing artifact (Tier 1), a light fresh read of the raw
CSV (Tier 2), or a rescoring pass against the saved model (Tier 3) — nothing is
hand-typed. Re-run any script at any time to regenerate its outputs. The consolidated
workflow + verified numbers live in the repo-root [`RESULTS.md`](../RESULTS.md).

## Status

| # | Section | Deliverable | Script | Status |
|---|---|---|---|---|
| 1 | ۴-۲-۲ | `tables/4_2_2_dataset_overview.md` | `t2_dataset_stats.py` | ✅ done |
| 2 | ۴-۲-۲ | `figures/4_2_2_class_balance_4way.png` | `t2_dataset_stats.py` | ✅ done |
| 3 | ۴-۲-۲ | `figures/4_2_2_failure_rate_by_language.png` | `t2_dataset_stats.py` | ✅ done |
| 4 | ۴-۲-۴ | `tables/4_2_4_leakage_verification.md` | `t1_leakage_verification.py` | ✅ done |
| 5 | ۴-۳-۱ | `tables/4_3_1_final_model_config.md` | `t1_final_model_config.py` | ✅ done |
| 6 | ۴-۳-۲ | `tables/4_3_2_grid_search_top_configs.md` | `t1_grid_search_top_configs.py` | ✅ done |
| 7 | ۴-۳-۲ | `figures/4_3_2_grid_search_top_configs.png` | `t1_grid_search_top_configs.py` | ✅ done |
| 8 | ۴-۳-۳ | calibration curve (val+test) | *(already existed)* | ✅ `artifacts/calibration_curve.png` |
| 9 | ۴-۳-۴ | threshold sweep (precision/recall/F1) | *(already existed)* | ✅ `artifacts/threshold_sweep_val.png` |
| 10 | ۴-۴-۱ | `tables/4_4_1_metrics_by_split.md` | `t1_metrics_comparison_chart.py` | ✅ done |
| 11 | ۴-۴-۱ | `figures/4_4_1_metrics_comparison.png` | `t1_metrics_comparison_chart.py` | ✅ done |
| 12 | ۴-۴-۱ | `figures/4_4_1_roc_curve_test.png` | `t3_rescore_curves.py` | ✅ done (sanity-checked: rescored ROC-AUC/PR-AUC/Brier match `metrics.json` to 6 decimals) |
| 13 | ۴-۴-۱ | `figures/4_4_1_pr_curve_test.png` | `t3_rescore_curves.py` | ✅ done |
| 14 | ۴-۴-۱ | `figures/4_4_1_prob_distribution_test.png` | `t3_rescore_curves.py` | ✅ done |
| 15 | ۴-۴-۲ | 3-state confusion table+figure | *(already existed)* | ✅ `artifacts/three_state_confusion_test.png` |
| 16 | ۴-۴-۳ | `tables/4_4_3_top10_rf_importance.md` | `t1_importance_shap_tables.py` | ✅ done |
| 17 | ۴-۴-۳ | `tables/4_4_3_top8_shap.md` | `t1_importance_shap_tables.py` | ✅ done |
| 18 | ۴-۴-۳ | RF importance / SHAP summary figures | *(already existed)* | ✅ `artifacts/feature_importance.png`, `artifacts/shap_summary.png` |
| 19 | ۴-۵ | `tables/4_5_ablation_summary.md`, `figures/4_5_ablation_summary.png` | `t4b_diffonly_random_diagnostic.py`, `t4c_ablation_summary.py` | ✅ done |
| 20 | ۴-۶ | `tables/4_6_5_realworld_case_study.md`, `figures/4_6_5_realworld_case_study.png` | demo-app + `t5_realworld_case_study.py` | ⚠️ superseded — §۴-۶ now uses the online campaign (`campaign/results/FINAL.md`); kept as evidence only |
| 21 | ۴-۷ | `tables/4_7_1_llm_example_*.md`, `tables/4_7_2_llm_qualitative_rubric.md` | `t6_llm_examples.py` | ✅ done — 2 real examples via Hermes CLI (NVIDIA NIM, Llama-3.3-Nemotron) |
| 22 | ۴-۷-۳ | `tables/4_7_3_batch20_summary.md` + `tables/4_7_3_batch20/example_*.md` | `t7_llm_batch_eval.py` + `t7b_compile_batch_summary.py` | ✅ done — 13 of 20 planned real held-out test builds (stopped early on a Hermes 180s timeout on #14; 13 judged sufficient) |
| 23 | ۴-۷-۴ | `tables/4_7_4_v2_comparison_*.md` — developer-facing prompt v2, verified before/after | `t8_llm_prompt_v2_comparison.py` | ✅ done — `LLM_PROMPT.md` now contains ONLY the final (v2) prompt; the thesis (§۴-۷-۲) embeds two LIVE campaign examples (`campaign/results/llm_examples/`), not these test-set ones |
| 24 | ۴-۷-۵ | `tables/4_7_5_conditional_policy_test.md` — 1 PASS (skipped) / 1 WARN / 1 ROLLBACK, real test-set builds | `t9_conditional_llm_test.py` | ✅ done — confirms the "LLM only for WARN/ROLLBACK" gating policy works correctly |
| 25 | ۴-۲-۳ | `tables/4_2_3_split_table.md` | `t1_split_table.py` | ✅ done — caught in the critical review pass, was marked READY but never actually generated |
| 26 | ۴-۳-۴ | `tables/4_3_4_threshold_policy.md` | `t1_threshold_policy_table.py` | ✅ done — same as above |
| 27 | ۴-۴-۲ | `tables/4_4_2_three_state_confusion.md` (raw counts + derived rates: ROLLBACK precision, failures-flagged %, false-pass rate) | `t1_confusion_table.py` | ✅ done — the derived rates are new value beyond the existing figure, not redundant |
| — | ۴-۲-۳ | split-size/failure-rate figure | *(deliberately skipped)* | ⬜ **not made, on purpose** — critical review judged it redundant with the split table above (5 similarly-sized bars reveal no pattern a table doesn't already show); do not re-add without a concrete reason |

## Folder layout

```
chapter4/
  scripts/   one script per deliverable, re-runnable, no hand-edited numbers
  tables/    generated .md tables (source of truth for thesis table text)
  figures/   generated .png charts (source of truth for thesis figures)
  data/      intermediate arrays saved so expensive steps aren't repeated
             (e.g. rescored_val.npz / rescored_test.npz: raw y, calibrated p)
```

## Real-world case study — 5 real GitHub Actions runs (SUPERSEDED as thesis content)

> **⚠️ Superseded (2026-07-10):** thesis §۴-۶ no longer presents this 5-commit case
> study. It was replaced by the full online evaluation campaign — 9 repos × 50 commits,
> shadow-mode gate, 271 scored builds — whose final numbers live in
> **`campaign/results/FINAL.md`** and whose thesis text is in `chapter4_v2.docx` §۴-۶.
> Everything below is kept as historical evidence of the first live deployment only.

Demo repo: **https://github.com/novavisionstudio-byte/bfp-cicd-risk-gate-demo**
(`demo-app/` locally, vendors the trained model + `bfp` inference code, has its own
`.github/workflows/risk-gate.yml`). 6 commits were pushed one at a time (so each got
its own real Actions run); commit 1's run was invalidated by two infra bugs found and
fixed live (see the note in `tables/4_6_5_realworld_case_study.md`), so the clean case
study covers commits 2-6, saved verbatim in `demo-app/ci_gate_runs/commit{2..6}/`:

| Commit | Gate decision | p(fail) | What actually happened |
|---|---|---|---|
| 2. Add factorial + tests | PASS | 0.074 | tests pass |
| 3. Expose factorial via API | PASS | 0.079 | tests pass |
| 4. Add stats module (large diff, light tests) | PASS | 0.081 | tests pass |
| 5. Remove divide-by-zero exception (small, dangerous diff) | PASS | 0.051 | **tests genuinely fail** (gate missed it) |
| 6. Restore the exception (fix) | **ROLLBACK** | 0.514 | test job **skipped** — gate stopped the pipeline before it ran, from real `hist_prev_status`/`hist_consec_fail` signal |

Commits 2-4 show diff-only signal is weak live, exactly matching the ablation
result. Commit 5 shows a real blind spot (small semantic change, no diff/history
signal to catch it). Commit 6 is the payoff: the *only* thing that changed between
commit 5 (PASS) and commit 6 (ROLLBACK) is that commit 5's test genuinely failed in
between — real accumulated history, not a bigger diff, is what moved the decision.

## Reproducing everything

```
cd "pipeline cicd project"
.venv/Scripts/python.exe chapter4/scripts/t1_leakage_verification.py
.venv/Scripts/python.exe chapter4/scripts/t1_final_model_config.py
.venv/Scripts/python.exe chapter4/scripts/t1_grid_search_top_configs.py
.venv/Scripts/python.exe chapter4/scripts/t1_metrics_comparison_chart.py
.venv/Scripts/python.exe chapter4/scripts/t1_importance_shap_tables.py
.venv/Scripts/python.exe chapter4/scripts/t2_dataset_stats.py
.venv/Scripts/python.exe chapter4/scripts/t3_rescore_curves.py   # slow: reloads the 3.55GB CSV

# Tier 4 (ablation re-runs) -- must run in this order, ~10-15 min total
BFP_USE_HISTORY=0 \
BFP_MODELS_DIR="$(pwd)/chapter4/ablation/diffonly_grouped/models" \
BFP_ARTIFACTS_DIR="$(pwd)/chapter4/ablation/diffonly_grouped/artifacts" \
.venv/Scripts/python.exe run_offline.py                       # diff-only, grouped split
.venv/Scripts/python.exe chapter4/scripts/t4b_diffonly_random_diagnostic.py  # diff-only, random split
.venv/Scripts/python.exe chapter4/scripts/t4c_ablation_summary.py            # compile table + figure
```

## Tier 4 note: `bfp/config.py` now supports env-var overrides

`MODELS_DIR`, `ARTIFACTS_DIR`, and `USE_HISTORY` are now overridable via
`BFP_MODELS_DIR` / `BFP_ARTIFACTS_DIR` / `BFP_USE_HISTORY` env vars (defaults
unchanged, so the main pipeline and all 9 tests behave exactly as before). This is
what let the diff-only ablation run write to `chapter4/ablation/diffonly_grouped/`
instead of overwriting the main `artifacts/`/`models/`.

## Ablation results (section 4-5) -- now fully reproducible

| Configuration | ROC-AUC | PR-AUC | Brier |
|---|---|---|---|
| Diff-only, grouped split | 0.5149 | 0.2516 | 0.1887 |
| Diff-only, random split (diagnostic) | 0.8332 | 0.6938 | — |
| Diff+history, grouped split (final model) | 0.8602 | 0.7489 | 0.1105 |

The diff-only/grouped re-run reproduces the historical HANDOFF.md number (0.515) almost
exactly. The random-split diagnostic additionally reports that 929/930 (99.9%) of
test-split projects also appear in train under a random split (vs. 0% under grouped,
by construction) — the concrete mechanism behind the leakage gap.
Full detail: `tables/4_5_ablation_summary.md`, `figures/4_5_ablation_summary.png`.
