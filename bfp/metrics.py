"""Evaluation metrics and curve data for Chapter 4.

Threshold-free metrics (ROC-AUC, PR-AUC, Brier) use the calibrated probability.
Threshold-based metrics (F1, Precision, Recall, MCC, confusion) are reported at
tau1 (the WARN boundary = "flag this build as risky"). F1/MCC are reported only;
they are NOT used to choose thresholds.
"""
from __future__ import annotations
import numpy as np
from sklearn.metrics import (roc_auc_score, average_precision_score, brier_score_loss,
                             f1_score, precision_score, recall_score,
                             matthews_corrcoef, confusion_matrix)
from . import config as C


def threshold_free(y, probs) -> dict:
    y = np.asarray(y); probs = np.asarray(probs)
    return {
        "roc_auc": float(roc_auc_score(y, probs)),
        "pr_auc": float(average_precision_score(y, probs)),
        "brier": float(brier_score_loss(y, probs)),
        "base_rate": float(y.mean()),
    }


def binary_at_threshold(y, probs, tau) -> dict:
    y = np.asarray(y); pred = (np.asarray(probs) >= tau).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "threshold": float(tau),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "mcc": float(matthews_corrcoef(y, pred)) if len(np.unique(pred)) > 1 else 0.0,
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def three_state_confusion(y, decisions) -> dict:
    """Rows = actual (pass=0 / fail=1), cols = PASS/WARN/ROLLBACK."""
    y = np.asarray(y); decisions = np.asarray(decisions)
    out = {}
    for actual, name in [(0, "actual_pass"), (1, "actual_fail")]:
        m = y == actual
        out[name] = {lab: int((decisions[m] == lab).sum()) for lab in C.DECISION_LABELS}
    return out


def calibration_curve_data(y, probs, n_bins=10) -> dict:
    y = np.asarray(y); probs = np.asarray(probs)
    edges = np.linspace(0, 1, n_bins + 1)
    idx = np.clip(np.digitize(probs, edges) - 1, 0, n_bins - 1)
    rows = []
    for b in range(n_bins):
        m = idx == b
        if m.sum() == 0:
            continue
        rows.append({"bin_lo": float(edges[b]), "bin_hi": float(edges[b + 1]),
                     "mean_pred": float(probs[m].mean()),
                     "frac_pos": float(y[m].mean()), "count": int(m.sum())})
    return {"bins": rows}


def sweep_table(y, probs, steps=C.THRESH_GRID_STEPS) -> list:
    y = np.asarray(y); probs = np.asarray(probs)
    grid = np.linspace(0, 1, steps)
    rows = []
    P = y.sum()
    for tau in grid:
        pred = probs >= tau
        tp = int((pred & (y == 1)).sum()); fp = int((pred & (y == 0)).sum())
        fn = int(P - tp)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        rows.append({"threshold": float(tau), "precision": prec, "recall": rec, "f1": f1})
    return rows
