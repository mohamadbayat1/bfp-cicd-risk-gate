"""Chapter 4, section 4-4-1: ROC curve, PR curve, calibrated-probability histogram.

Tier 3 (RESCORE): these curves were never persisted by run_offline.py (only the
scalar ROC-AUC/PR-AUC are saved in metrics.json). This script reloads the raw data,
reproduces the EXACT same deterministic split (same seed=42, same bfp.splits code),
reloads the SAVED preprocessor/model/calibrator (no retraining), rescoring the
val/test splits, and:
  1. sanity-checks the rescored ROC-AUC/PR-AUC/Brier against artifacts/metrics.json
     (must match to confirm this is a faithful reproduction, not a different run),
  2. saves the raw (y, p) arrays for val/test to chapter4/data/ so this never has to
     be rescored again,
  3. plots the ROC curve, PR curve, and calibrated-probability histogram (pass vs
     fail) for the test split.
"""
from __future__ import annotations
import os, sys, json, datetime
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from bfp import config as C, data, splits, model as Model  # noqa: E402
from bfp.preprocess import Preprocessor  # noqa: E402

DATA_DIR = os.path.join(ROOT, "chapter4", "data")
FIG_DIR = os.path.join(ROOT, "chapter4", "figures")


def log(msg):
    print(f"[{datetime.datetime.now().isoformat(timespec='seconds')}] {msg}", flush=True)


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(FIG_DIR, exist_ok=True)

    log("loading + cleaning full dataset (chunked, stream-dedup to build level)")
    df = data.load_builds()
    log(f"builds={len(df)}")

    log("reproducing the exact grouped split (seed=42)")
    sp = splits.make_splits(df)
    splits.assert_no_group_overlap(sp)

    log("loading SAVED preprocessor / model / calibrator (no retraining)")
    pre = Preprocessor.load(os.path.join(ROOT, "models", "preprocessor.joblib"))
    import joblib
    rf = joblib.load(os.path.join(ROOT, "models", "rf_model.joblib"))
    cal = joblib.load(os.path.join(ROOT, "models", "calibrator.joblib"))

    results = {}
    for name in ("val", "test"):
        X = pre.transform(sp[name])
        y = sp[name]["y"].to_numpy()
        p = cal.transform(Model.rf_pos_proba(rf, X))
        results[name] = (y, p)
        np.savez(os.path.join(DATA_DIR, f"rescored_{name}.npz"), y=y, p=p)
        log(f"{name}: rescored n={len(y)}, saved to chapter4/data/rescored_{name}.npz")

    # ---------------------------------------------------------- sanity check vs metrics.json
    from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
    with open(os.path.join(ROOT, "artifacts", "metrics.json")) as f:
        saved_metrics = json.load(f)

    for name in ("val", "test"):
        y, p = results[name]
        roc = roc_auc_score(y, p)
        pr = average_precision_score(y, p)
        brier = brier_score_loss(y, p)
        ref = saved_metrics[name]["threshold_free"]
        log(f"{name}: rescored ROC-AUC={roc:.6f} (saved={ref['roc_auc']:.6f}), "
            f"PR-AUC={pr:.6f} (saved={ref['pr_auc']:.6f}), "
            f"Brier={brier:.6f} (saved={ref['brier']:.6f})")
        assert abs(roc - ref["roc_auc"]) < 1e-6, f"{name}: ROC-AUC mismatch -- rescore is NOT faithful"
        assert abs(pr - ref["pr_auc"]) < 1e-6, f"{name}: PR-AUC mismatch -- rescore is NOT faithful"
        assert abs(brier - ref["brier"]) < 1e-6, f"{name}: Brier mismatch -- rescore is NOT faithful"
    log("sanity check PASSED: rescored probabilities exactly reproduce artifacts/metrics.json")

    # ---------------------------------------------------------------- plots (test split)
    from sklearn.metrics import roc_curve, precision_recall_curve
    y_test, p_test = results["test"]

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fpr, tpr, _ = roc_curve(y_test, p_test)
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot(fpr, tpr, label=f"RF+Platt (AUC={roc_auc_score(y_test, p_test):.3f})")
    ax.plot([0, 1], [0, 1], "k--", lw=1, label="chance")
    ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate")
    ax.set_title("ROC curve (test)"); ax.legend()
    fig.tight_layout(); fig.savefig(os.path.join(FIG_DIR, "4_4_1_roc_curve_test.png"), dpi=120)
    plt.close(fig)

    prec, rec, _ = precision_recall_curve(y_test, p_test)
    fig, ax = plt.subplots(figsize=(5, 5))
    base_rate = y_test.mean()
    ax.plot(rec, prec, label=f"RF+Platt (AP={average_precision_score(y_test, p_test):.3f})")
    ax.axhline(base_rate, color="k", ls="--", lw=1, label=f"base rate ({base_rate:.3f})")
    ax.set_xlabel("Recall"); ax.set_ylabel("Precision")
    ax.set_title("Precision-Recall curve (test)"); ax.legend()
    fig.tight_layout(); fig.savefig(os.path.join(FIG_DIR, "4_4_1_pr_curve_test.png"), dpi=120)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    bins = np.linspace(0, 1, 41)
    ax.hist(p_test[y_test == 0], bins=bins, alpha=0.6, label="actual pass", color="seagreen",
            density=True)
    ax.hist(p_test[y_test == 1], bins=bins, alpha=0.6, label="actual fail", color="firebrick",
            density=True)
    ax.set_xlabel("Calibrated failure probability"); ax.set_ylabel("density")
    ax.set_title("Calibrated probability distribution by actual outcome (test)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "4_4_1_prob_distribution_test.png"), dpi=120)
    plt.close(fig)

    log("wrote 4_4_1_roc_curve_test.png, 4_4_1_pr_curve_test.png, 4_4_1_prob_distribution_test.png")


if __name__ == "__main__":
    main()
