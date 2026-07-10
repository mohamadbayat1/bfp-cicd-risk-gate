"""Chapter 4, section 4-3-1: final model configuration summary table.

Pure transcription from bfp/config.py (fixed RF settings, BETA, CV folds, subsample
size) + artifacts/metadata.json (chosen hyperparameters, CV F-beta). No computation,
no retraining.
"""
from __future__ import annotations
import json, os, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from bfp import config as C  # noqa: E402

OUT = os.path.join(ROOT, "chapter4", "tables", "4_3_1_final_model_config.md")


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(os.path.join(ROOT, "artifacts", "metadata.json")) as f:
        meta = json.load(f)
    best = meta["best_params"]
    search = meta["search"]

    rows = [
        ("Model", "RandomForestClassifier"),
        ("Split criterion", C.RF_FIXED["criterion"]),
        ("Class weighting", C.RF_FIXED["class_weight"]),
        ("Random state / seed", C.RF_FIXED["random_state"]),
        ("Cross-validation", f"StratifiedGroupKFold({C.CV_FOLDS})"),
        ("Search criterion", f"F-beta (beta={C.BETA})"),
        ("Search subsample size", C.GRID_SUBSAMPLE),
        ("Best CV F-beta (validation-fold mean)", round(search["best_cv_score"], 4)),
        ("n_estimators (chosen)", best["n_estimators"]),
        ("max_depth (chosen)", best["max_depth"]),
        ("min_samples_leaf (chosen)", best["min_samples_leaf"]),
        ("max_features (chosen)", best["max_features"]),
    ]

    lines = ["# 4-3-1 — Final model configuration & search process\n",
             f"_Generated: {datetime.datetime.now().isoformat(timespec='seconds')}_\n",
             "| Component | Value |", "|---|---|"]
    for k, v in rows:
        lines.append(f"| {k} | {v} |")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
