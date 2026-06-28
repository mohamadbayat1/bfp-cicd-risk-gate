"""Generate a human-readable Chapter-4 report (REPORT.md) from the saved artifacts.
Run AFTER run_offline.py. Reads only artifacts/ + models/ — no recomputation.
"""
import json, os
from bfp import config as C


def _load(path):
    with open(path) as f:
        return json.load(f)


def _row(name, tf, bm):
    cm = bm["confusion"]
    return (f"| {name} | {tf['roc_auc']:.4f} | {tf['pr_auc']:.4f} | {tf['brier']:.4f} | "
            f"{bm['precision']:.4f} | {bm['recall']:.4f} | {bm['f1']:.4f} | {bm['mcc']:.4f} | "
            f"{cm['tp']}/{cm['fp']}/{cm['fn']}/{cm['tn']} |")


def main():
    A = C.ARTIFACTS_DIR
    meta = _load(os.path.join(A, "metadata.json"))
    metrics = _load(os.path.join(A, "metrics.json"))
    imps = _load(os.path.join(A, "feature_importances.json"))
    shap_path = os.path.join(A, "shap_summary.json")
    shaps = _load(shap_path) if os.path.exists(shap_path) else None
    th = meta["thresholds"]

    L = []
    w = L.append
    w("# Chapter 4 — Results (auto-generated from artifacts)\n")
    w(f"_Seed {meta['seed']}. Versions: " +
      ", ".join(f"{k}={v}" for k, v in meta["versions"].items()) + "._\n")

    w("## Dataset & target")
    cb = meta["class_balance"]
    w(f"- Builds (after dedup to one row/build, dropping `started`): **{meta['n_builds']:,}**")
    w(f"- Target: `y=1` if `tr_status != 'passed'` (failed/errored/canceled), else 0.")
    w(f"- Class balance: {cb['positives']:,} failures / {cb['negatives']:,} passes "
      f"(failure rate **{cb['failure_rate']:.4f}**).\n")

    w("## Split (grouped by project, no project on two sides)")
    w("| split | builds | projects | failure_rate |")
    w("|---|---|---|---|")
    for k, v in meta["split_report"].items():
        w(f"| {k} | {v['builds']:,} | {v['projects']} | {v['failure_rate']:.4f} |")
    w("")

    w("## Model & tuning")
    s = meta["search"]
    w(f"- RandomForest (gini, class_weight=balanced, random_state={meta['seed']}).")
    w(f"- Grid search: {s['cv']}, scoring {s['scoring']}, on a stratified subsample of "
      f"{s['search_subsample_n']:,} (final model refit on the full training set).")
    w(f"- Search space: `{s['param_grid']}`")
    w(f"- **Chosen hyperparameters:** `{meta['best_params']}`  (CV F-beta={s['best_cv_score']:.4f})\n")

    w("## Calibration & decision policy")
    c = meta["constants"]
    w(f"- Platt scaling (logistic, no class weight) on a held-out calibration subset carved from train.")
    w(f"- Constants: BETA={c['BETA']}, r*={c['R_STAR']}, p*={c['P_STAR']}.")
    w(f"- Thresholds (selected on VALIDATION only): **τ1={th['tau1']:.4f}**, **τ2={th['tau2']:.4f}**.")
    w(f"  - Recall@τ1 = {th['recall_at_tau1']:.4f} (target r*={c['R_STAR']}); "
      f"Precision@τ2 = {th['precision_at_tau2']:.4f} (target p*={c['P_STAR']}).")
    w(f"  - Fallback used: {th['fallback']}.")
    w(f"- Decision: PASS if p<τ1; WARN if τ1≤p<τ2; ROLLBACK if p≥τ2.\n")

    w("## Metrics (threshold-based metrics at τ1; confusion as TP/FP/FN/TN)")
    w("| split | ROC-AUC | PR-AUC | Brier | Precision | Recall | F1 | MCC | TP/FP/FN/TN |")
    w("|---|---|---|---|---|---|---|---|---|")
    name_map = {"train_fit": "train", "val": "val", "test": "test"}
    for k in ("train_fit", "val", "test"):
        m = metrics[k]
        w(_row(name_map[k], m["threshold_free"], m["binary_at_tau1"]))
    w("")

    w("## Three-state decision confusion (test) — actual × decision")
    cm = metrics["test"]["three_state_confusion"]
    w("| actual \\ decision | PASS | WARN | ROLLBACK |")
    w("|---|---|---|---|")
    for actual, lab in (("actual_pass", "pass"), ("actual_fail", "fail")):
        r = cm[actual]
        w(f"| {lab} | {r['PASS']} | {r['WARN']} | {r['ROLLBACK']} |")
    w("")

    w("## Leakage alarm check")
    al = meta["alarms"]
    w(f"- Test ROC-AUC = {al['test_roc_auc']:.4f} (alarm if ≥ {C.ALARM_TEST_ROC_AUC}) → "
      f"{'TRIPPED' if al['alarm_roc_auc_tripped'] else 'OK'}")
    w(f"- Max single-feature importance = {al['max_feature_importance']:.4f} "
      f"(alarm if ≥ {C.ALARM_FEATURE_IMPORTANCE}) → "
      f"{'TRIPPED' if al['alarm_feature_importance_tripped'] else 'OK'}\n")

    w("## Top features — RF importance")
    w("| rank | feature | importance |")
    w("|---|---|---|")
    for i, d in enumerate(imps[:12], 1):
        w(f"| {i} | {d['feature']} | {d['importance']:.4f} |")
    w("")
    if shaps:
        w("## Top features — mean |TreeSHAP| (interventional, test sample)")
        w("| rank | feature | mean_abs_shap |")
        w("|---|---|---|")
        for i, d in enumerate(shaps[:12], 1):
            w(f"| {i} | {d['feature']} | {d['mean_abs_shap']:.5f} |")
        w("")

    w("## Figures (in `artifacts/`)")
    for fn in ("calibration_curve.png", "threshold_sweep_val.png",
               "feature_importance.png", "shap_summary.png",
               "three_state_confusion_test.png"):
        if os.path.exists(os.path.join(A, fn)):
            w(f"- `{fn}`")

    out = os.path.join(C.ROOT, "REPORT.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
