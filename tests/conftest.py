"""Shared fixture: build a small, fast, end-to-end pipeline ONCE and expose all
objects + a temp models dir. Tests assert leakage/consistency/reproducibility on it.
Uses a CSV prefix (many projects, since projects are interleaved) so it is quick but
exercises the full grouped-split + tune + calibrate + threshold + SHAP path.
"""
import os, sys, json, tempfile
import numpy as np
import pandas as pd
import joblib
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bfp import config as C
from bfp import data, splits, metrics as M
from bfp.preprocess import Preprocessor
from bfp import model as Model

QUICK_GRID = {"n_estimators": [120], "max_depth": [12],
              "min_samples_leaf": [10], "max_features": ["sqrt"]}
MAX_ROWS = 250_000


@pytest.fixture(scope="session")
def ctx():
    tmp = tempfile.mkdtemp(prefix="bfp_test_")
    C.MODELS_DIR = tmp
    C.ARTIFACTS_DIR = tmp
    C.ensure_dirs()

    df = data.load_builds(max_rows=MAX_ROWS)
    sp = splits.make_splits(df)
    pre = Preprocessor().fit(sp["train"])
    X = {k: pre.transform(sp[k]) for k in sp}
    y = {k: sp[k]["y"].to_numpy() for k in sp}
    g = {k: sp[k][C.KEY_GROUP].to_numpy() for k in sp}

    best_params, search_summary = Model.tune_rf(
        X["train_fit"], y["train_fit"], g["train_fit"],
        param_grid=QUICK_GRID, subsample=8000, verbose=0)
    rf = Model.fit_rf(X["train_fit"], y["train_fit"], best_params)
    cal = Model.PlattCalibrator().fit(Model.rf_pos_proba(rf, X["calib"]), y["calib"])
    p = {k: cal.transform(Model.rf_pos_proba(rf, X[k])) for k in ("train_fit", "val", "test")}
    tau1, tau2, thr_info = Model.select_thresholds(y["val"], p["val"])

    importances = sorted(
        [{"feature": f, "importance": float(v)} for f, v in zip(C.FEATURE_ORDER, rf.feature_importances_)],
        key=lambda d: -d["importance"])
    test_tf = M.threshold_free(y["test"], p["test"])

    # persist artifacts used by InferencePipeline + alarm test
    pre.save(os.path.join(tmp, "preprocessor.joblib"))
    joblib.dump(rf, os.path.join(tmp, "rf_model.joblib"))
    joblib.dump(cal, os.path.join(tmp, "calibrator.joblib"))
    with open(os.path.join(tmp, "thresholds.json"), "w") as f:
        json.dump({"tau1": tau1, "tau2": tau2, **thr_info}, f, default=float)
    bg_pool = X["train_fit"][y["train_fit"] == 0]
    bg = bg_pool.sample(n=min(50, len(bg_pool)), random_state=C.SEED)
    np.save(os.path.join(tmp, "shap_background.npy"), bg.to_numpy())

    return dict(df=df, sp=sp, pre=pre, X=X, y=y, g=g, rf=rf, cal=cal, p=p,
                tau1=tau1, tau2=tau2, thr_info=thr_info, best_params=best_params,
                importances=importances, max_imp=importances[0]["importance"],
                test_tf=test_tf, models_dir=tmp)
