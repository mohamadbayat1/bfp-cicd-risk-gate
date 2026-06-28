"""Offline training pipeline orchestrator.

Runs the whole Chapter-3 offline method end to end and writes every Chapter-4
artifact to disk. Usage:

    python run_offline.py                 # full run on all builds
    python run_offline.py --max-rows 150000 --quick   # fast smoke run

Stages: load+clean -> grouped split -> preprocess (fit on TRAIN only) ->
RF grid search (subsample) -> refit on full train -> Platt calibration ->
threshold sweep on VALIDATION -> TreeSHAP -> metrics + plots + metadata.
"""
from __future__ import annotations
import argparse, json, os, sys, time, platform
import numpy as np
import pandas as pd
import joblib

from bfp import config as C
from bfp import data, splits, metrics as M
from bfp.preprocess import Preprocessor
from bfp import model as Model


def _versions():
    import sklearn, shap, numpy, pandas, joblib as jl
    return {"python": platform.python_version(), "numpy": numpy.__version__,
            "pandas": pandas.__version__, "scikit_learn": sklearn.__version__,
            "shap": shap.__version__, "joblib": jl.__version__}


def _save_json(obj, path):
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=float)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-rows", type=int, default=None,
                    help="limit job-rows read (for fast runs)")
    ap.add_argument("--quick", action="store_true",
                    help="smaller grid + subsample for a fast smoke run")
    ap.add_argument("--no-plots", action="store_true")
    args = ap.parse_args()

    C.ensure_dirs()
    t0 = time.time()
    log = lambda m: print(f"[{time.time()-t0:6.0f}s] {m}", flush=True)

    # ----------------------------------------------------------------- load + clean
    log("loading + cleaning (chunked, stream-dedup to build level)")
    df = data.load_builds(max_rows=args.max_rows, verbose=False)
    log(f"builds={len(df)}  {data.class_balance(df)}")

    # ----------------------------------------------------------------- split
    sp = splits.make_splits(df)
    splits.assert_no_group_overlap(sp)
    split_rep = splits.split_report(sp)
    log(f"split: {split_rep}")

    # ----------------------------------------------------------------- preprocess (fit on TRAIN only)
    pre = Preprocessor().fit(sp["train"])
    X = {k: pre.transform(sp[k]) for k in sp}
    y = {k: sp[k]["y"].to_numpy() for k in sp}
    g = {k: sp[k][C.KEY_GROUP].to_numpy() for k in sp}

    # ----------------------------------------------------------------- tune RF (subsample) on train_fit
    grid = {"n_estimators": [200], "max_depth": [None, 16], "min_samples_leaf": [5],
            "max_features": ["sqrt"]} if args.quick else C.PARAM_GRID
    sub = 15000 if args.quick else C.GRID_SUBSAMPLE
    log("grid search (StratifiedGroupKFold, F-beta) on stratified subsample")
    best_params, search_summary = Model.tune_rf(
        X["train_fit"], y["train_fit"], g["train_fit"], param_grid=grid,
        subsample=sub, verbose=1)
    log(f"best_params={best_params}  cv_fbeta={search_summary['best_cv_score']:.4f}")

    # ----------------------------------------------------------------- refit on full train_fit
    log("refitting RF on full train_fit")
    rf = Model.fit_rf(X["train_fit"], y["train_fit"], best_params)

    # feature importance + leakage alarm
    importances = sorted(
        [{"feature": f, "importance": float(v)}
         for f, v in zip(C.FEATURE_ORDER, rf.feature_importances_)],
        key=lambda d: -d["importance"])
    max_imp = importances[0]["importance"]

    # ----------------------------------------------------------------- Platt calibration on calib subset
    log("Platt calibration on held-out calibration subset")
    cal = Model.PlattCalibrator().fit(Model.rf_pos_proba(rf, X["calib"]), y["calib"])

    def calibrated(split):
        return cal.transform(Model.rf_pos_proba(rf, X[split]))

    p = {k: calibrated(k) for k in ("train_fit", "val", "test")}

    # ----------------------------------------------------------------- thresholds on VALIDATION only
    tau1, tau2, thr_info = Model.select_thresholds(y["val"], p["val"])
    log(f"thresholds: tau1={tau1:.4f} tau2={tau2:.4f} fallback={thr_info['fallback']}")

    # ----------------------------------------------------------------- TreeSHAP (interventional)
    log("TreeSHAP (interventional) attribution")
    shap_summary = None
    try:
        bg_pool = X["train_fit"][y["train_fit"] == 0]
        bg = bg_pool.sample(n=min(C.SHAP_BACKGROUND, len(bg_pool)), random_state=C.SEED)
        n_exp = min(C.SHAP_EXPLAIN_N, len(X["test"]))
        X_exp = X["test"].sample(n=n_exp, random_state=C.SEED)
        shap_summary, _, _ = Model.treeshap_summary(rf, bg, X_exp, C.FEATURE_ORDER)
        np.save(os.path.join(C.MODELS_DIR, "shap_background.npy"), bg.to_numpy())
    except Exception as e:
        log(f"WARNING: SHAP failed: {e}")

    # ----------------------------------------------------------------- metrics (train/val/test)
    log("computing metrics")
    results = {}
    for name in ("train_fit", "val", "test"):
        dec = Model.decide(p[name], tau1, tau2)
        results[name] = {
            "threshold_free": M.threshold_free(y[name], p[name]),
            "binary_at_tau1": M.binary_at_threshold(y[name], p[name], tau1),
            "three_state_confusion": M.three_state_confusion(y[name], dec),
            "calibration_curve": M.calibration_curve_data(y[name], p[name]),
        }
    sweep = M.sweep_table(y["val"], p["val"])

    # leakage alarm flags (verification test #2 reads these)
    test_auc = results["test"]["threshold_free"]["roc_auc"]
    alarms = {
        "test_roc_auc": test_auc,
        "max_feature_importance": max_imp,
        "alarm_roc_auc_tripped": bool(test_auc >= C.ALARM_TEST_ROC_AUC),
        "alarm_feature_importance_tripped": bool(max_imp >= C.ALARM_FEATURE_IMPORTANCE),
    }
    if alarms["alarm_roc_auc_tripped"] or alarms["alarm_feature_importance_tripped"]:
        log(f"!!! LEAKAGE ALARM: {alarms} -- investigate before trusting results")

    # ----------------------------------------------------------------- save models + artifacts
    log("saving models + artifacts")
    pre.save(os.path.join(C.MODELS_DIR, "preprocessor.joblib"))
    joblib.dump(rf, os.path.join(C.MODELS_DIR, "rf_model.joblib"))
    joblib.dump(cal, os.path.join(C.MODELS_DIR, "calibrator.joblib"))
    _save_json({"tau1": tau1, "tau2": tau2, **thr_info}, os.path.join(C.MODELS_DIR, "thresholds.json"))
    _save_json({"feature_order": C.FEATURE_ORDER}, os.path.join(C.MODELS_DIR, "feature_order.json"))

    _save_json(results, os.path.join(C.ARTIFACTS_DIR, "metrics.json"))
    _save_json(importances, os.path.join(C.ARTIFACTS_DIR, "feature_importances.json"))
    if shap_summary is not None:
        _save_json(shap_summary, os.path.join(C.ARTIFACTS_DIR, "shap_summary.json"))
    pd.DataFrame(sweep).to_csv(os.path.join(C.ARTIFACTS_DIR, "threshold_sweep_val.csv"), index=False)

    metadata = {
        "versions": _versions(),
        "seed": C.SEED,
        "n_builds": int(len(df)),
        "class_balance": data.class_balance(df),
        "split_report": split_rep,
        "target": {"positive": "tr_status != 'passed'", "dropped_status": list(C.DROP_STATUS)},
        "feature_order": C.FEATURE_ORDER,
        "leakage_drop_list": C.LEAKAGE_DROP,
        "search": search_summary,
        "best_params": best_params,
        "constants": {"BETA": C.BETA, "R_STAR": C.R_STAR, "P_STAR": C.P_STAR},
        "thresholds": {"tau1": tau1, "tau2": tau2, **thr_info},
        "alarms": alarms,
        "elapsed_sec": round(time.time() - t0, 1),
    }
    _save_json(metadata, os.path.join(C.ARTIFACTS_DIR, "metadata.json"))

    if not args.no_plots:
        try:
            _plots(results, sweep, importances, shap_summary, tau1, tau2)
            log("plots saved")
        except Exception as e:
            log(f"WARNING: plotting failed: {e}")

    log(f"DONE. test metrics: {results['test']['threshold_free']}")
    print("\n=== SUMMARY (test) ===")
    print(json.dumps(results["test"], indent=2, default=float))


def _plots(results, sweep, importances, shap_summary, tau1, tau2):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # calibration curve (val + test)
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot([0, 1], [0, 1], "k--", lw=1, label="perfect")
    for name in ("val", "test"):
        b = results[name]["calibration_curve"]["bins"]
        ax.plot([r["mean_pred"] for r in b], [r["frac_pos"] for r in b], "o-", label=name)
    ax.set_xlabel("mean predicted prob"); ax.set_ylabel("observed failure freq")
    ax.set_title("Calibration"); ax.legend()
    fig.tight_layout(); fig.savefig(os.path.join(C.ARTIFACTS_DIR, "calibration_curve.png"), dpi=120)
    plt.close(fig)

    # threshold sweep (val)
    s = pd.DataFrame(sweep)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(s["threshold"], s["precision"], label="precision")
    ax.plot(s["threshold"], s["recall"], label="recall")
    ax.plot(s["threshold"], s["f1"], label="f1")
    ax.axvline(tau1, color="green", ls="--", label="tau1")
    ax.axvline(tau2, color="red", ls="--", label="tau2")
    ax.set_xlabel("threshold"); ax.set_title("Validation threshold sweep"); ax.legend()
    fig.tight_layout(); fig.savefig(os.path.join(C.ARTIFACTS_DIR, "threshold_sweep_val.png"), dpi=120)
    plt.close(fig)

    # feature importance (top 15)
    top = importances[:15][::-1]
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.barh([d["feature"] for d in top], [d["importance"] for d in top])
    ax.set_title("RF feature importance (top 15)")
    fig.tight_layout(); fig.savefig(os.path.join(C.ARTIFACTS_DIR, "feature_importance.png"), dpi=120)
    plt.close(fig)

    # SHAP summary (top 15)
    if shap_summary is not None:
        top = shap_summary[:15][::-1]
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.barh([d["feature"] for d in top], [d["mean_abs_shap"] for d in top], color="purple")
        ax.set_title("Mean |TreeSHAP| (top 15)")
        fig.tight_layout(); fig.savefig(os.path.join(C.ARTIFACTS_DIR, "shap_summary.png"), dpi=120)
        plt.close(fig)

    # 3-state confusion (test) as text-ish heatmap
    cm = results["test"]["three_state_confusion"]
    mat = np.array([[cm["actual_pass"][l] for l in C.DECISION_LABELS],
                    [cm["actual_fail"][l] for l in C.DECISION_LABELS]])
    fig, ax = plt.subplots(figsize=(5, 3))
    im = ax.imshow(mat, cmap="Blues")
    ax.set_xticks(range(3)); ax.set_xticklabels(C.DECISION_LABELS)
    ax.set_yticks([0, 1]); ax.set_yticklabels(["actual_pass", "actual_fail"])
    for i in range(2):
        for j in range(3):
            ax.text(j, i, str(mat[i, j]), ha="center", va="center")
    ax.set_title("Test: actual vs decision"); fig.colorbar(im)
    fig.tight_layout(); fig.savefig(os.path.join(C.ARTIFACTS_DIR, "three_state_confusion_test.png"), dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    main()
