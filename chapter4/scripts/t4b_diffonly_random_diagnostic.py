"""Chapter 4, section 4-5: diff-only + RANDOM (non-grouped) split diagnostic.

This is the third row of the ablation table -- explicitly a DIAGNOSTIC, not a
candidate model. It isolates the effect of the split strategy alone: same diff-only
feature set and the SAME hyperparameters chosen for the diff-only/grouped ablation
run (chapter4/ablation/diffonly_grouped/), but the split ignores project grouping
entirely (plain stratified random split). If ROC-AUC jumps far above the grouped
result on identical features/hyperparameters, the gap is project-identity leakage,
not real signal.

Must be run with BFP_USE_HISTORY=0 already set by run_diffonly_random.sh /
called after t1 (diffonly_grouped) has produced its best_params.
"""
from __future__ import annotations
import os

os.environ["BFP_USE_HISTORY"] = "0"   # must be set BEFORE importing bfp (config reads it at import time)

import sys, json, datetime
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, average_precision_score

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from bfp import config as C, data, model as Model  # noqa: E402
from bfp.preprocess import Preprocessor  # noqa: E402

assert C.USE_HISTORY is False, "USE_HISTORY must be False for this diagnostic"

GROUPED_DIR = os.path.join(ROOT, "chapter4", "ablation", "diffonly_grouped")
OUT_DIR = os.path.join(ROOT, "chapter4", "ablation", "diffonly_random")
SEED = C.SEED


def log(msg):
    print(f"[{datetime.datetime.now().isoformat(timespec='seconds')}] {msg}", flush=True)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    with open(os.path.join(GROUPED_DIR, "artifacts", "metadata.json")) as f:
        grouped_meta = json.load(f)
    best_params = grouped_meta["best_params"]
    log(f"reusing diff-only best_params from grouped ablation run: {best_params}")

    log("loading full dataset with USE_HISTORY=False (diff-only features)")
    df = data.load_builds()
    assert "hist_prev_status" not in df.columns, "history columns leaked in despite USE_HISTORY=False"
    log(f"builds={len(df)}, feature_order={C.FEATURE_ORDER}")

    # random (non-grouped) stratified split -- deliberately ignores project identity
    train_df, test_df = train_test_split(
        df, test_size=0.15, stratify=df["y"], random_state=SEED, shuffle=True)
    log(f"random split: train={len(train_df)}, test={len(test_df)}")

    # quantify the project overlap this split creates (the leakage mechanism, made concrete)
    train_projects = set(train_df[C.KEY_GROUP].unique())
    test_projects = set(test_df[C.KEY_GROUP].unique())
    overlap = train_projects & test_projects
    overlap_pct_of_test_projects = len(overlap) / len(test_projects) if test_projects else 0.0

    pre = Preprocessor().fit(train_df)
    X_train = pre.transform(train_df)
    X_test = pre.transform(test_df)
    y_train = train_df["y"].to_numpy()
    y_test = test_df["y"].to_numpy()

    log("fitting RF with the diff-only-grouped-tuned hyperparameters (no re-tuning)")
    rf = Model.fit_rf(X_train, y_train, best_params)
    p_test = Model.rf_pos_proba(rf, X_test)   # raw RF proba: calibration is a monotonic
                                               # transform and does not change ROC-AUC/PR-AUC

    roc = float(roc_auc_score(y_test, p_test))
    pr = float(average_precision_score(y_test, p_test))
    log(f"random-split diff-only: ROC-AUC={roc:.4f}, PR-AUC={pr:.4f}")
    log(f"project overlap: {len(overlap)}/{len(test_projects)} "
        f"({overlap_pct_of_test_projects:.1%}) of test-split projects also appear in train "
        f"(0% under the grouped split, by construction)")

    out = {
        "provenance": "DIAGNOSTIC — random (non-grouped) split on diff-only features; "
                       "NOT a candidate model; demonstrates project-identity leakage under "
                       "naive splitting. Same features + same hyperparameters as the "
                       "diff-only/grouped ablation row; only the split strategy differs.",
        "params_used": best_params,
        "n_train": int(len(train_df)),
        "n_test": int(len(test_df)),
        "roc_auc": roc,
        "pr_auc": pr,
        "brier": None,
        "project_overlap": {
            "train_projects": len(train_projects),
            "test_projects": len(test_projects),
            "overlap_projects": len(overlap),
            "overlap_pct_of_test_projects": overlap_pct_of_test_projects,
        },
        "seed": SEED,
    }
    with open(os.path.join(OUT_DIR, "metrics.json"), "w") as f:
        json.dump(out, f, indent=2)
    log(f"wrote {os.path.join(OUT_DIR, 'metrics.json')}")


if __name__ == "__main__":
    main()
