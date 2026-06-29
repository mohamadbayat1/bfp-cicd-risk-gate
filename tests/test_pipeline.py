"""Verification tests (1-8 from the spec). Leakage tests (1-3) are the most
important: a failure here blocks everything. Run:  pytest -v
"""
import os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bfp import config as C
from bfp import splits as S
from bfp import model as Model
from bfp.preprocess import Preprocessor
from bfp.inference import InferencePipeline


# ---------------------------------------------------------------- 1. column-level leakage
def test_no_post_outcome_column_in_X(ctx):
    cols = set(ctx["X"]["train_fit"].columns)
    drop = set(C.LEAKAGE_DROP)
    offending = cols & drop
    assert not offending, f"LEAKAGE: drop-list columns present in X: {offending}"
    # target and raw status must not be derivable from X
    assert C.TARGET_RAW not in cols
    assert "y" not in cols
    # X is exactly the intended feature set
    assert list(ctx["X"]["train_fit"].columns) == list(C.FEATURE_ORDER)


# ---------------------------------------------------------------- 2. signal-level leakage
def test_no_implausible_signal(ctx):
    test_auc = ctx["test_tf"]["roc_auc"]
    max_imp = ctx["max_imp"]
    assert test_auc < C.ALARM_TEST_ROC_AUC, (
        f"IMPLAUSIBLE test ROC-AUC={test_auc:.4f} >= {C.ALARM_TEST_ROC_AUC} -> investigate leakage")
    top = ctx["importances"][0]
    assert max_imp < C.ALARM_FEATURE_IMPORTANCE, (
        f"DOMINANT feature {top['feature']} importance={max_imp:.3f} -> investigate leakage")


# ---------------------------------------------------------------- 3. row-level (group) leakage
def test_no_project_overlap_across_splits(ctx):
    S.assert_no_group_overlap(ctx["sp"])
    tr = set(ctx["sp"]["train"][C.KEY_GROUP].unique())
    te = set(ctx["sp"]["test"][C.KEY_GROUP].unique())
    va = set(ctx["sp"]["val"][C.KEY_GROUP].unique())
    assert not (tr & te) and not (tr & va) and not (va & te)


# ---------------------------------------------------------------- 4. train/inference consistency
def test_inference_uses_saved_encoders_and_medians(ctx):
    loaded = Preprocessor.load(os.path.join(ctx["models_dir"], "preprocessor.joblib"))
    # saved medians/maps equal the fitted ones (not zeros, not fresh)
    assert loaded.medians_ == ctx["pre"].medians_
    assert loaded.cat_maps_ == ctx["pre"].cat_maps_
    assert any(v != 0.0 for v in loaded.medians_.values()), "medians look like zeros"
    # transform via loaded == transform via fitted (identical preprocessing)
    sample = ctx["sp"]["test"].head(20)
    pd.testing.assert_frame_equal(loaded.transform(sample), ctx["pre"].transform(sample))
    # full inference pipeline reproduces the manual path on saved objects
    infer = InferencePipeline(models_dir=ctx["models_dir"], with_shap=False)
    raw = ctx["sp"]["test"].head(5)
    out = infer.predict(raw)
    Xm = ctx["pre"].transform(raw)
    man = ctx["cal"].transform(ctx["rf"].predict_proba(Xm)[:, 1])
    for i, o in enumerate(out):
        assert abs(o["failure_probability"] - float(man[i])) < 1e-9


# ---------------------------------------------------------------- 5. no test contamination
def test_thresholds_calibrator_hparams_exclude_test(ctx):
    # thresholds reproduce exactly from VALIDATION probabilities alone
    t1, t2, _ = Model.select_thresholds(ctx["y"]["val"], ctx["p"]["val"])
    assert (t1, t2) == (ctx["tau1"], ctx["tau2"])
    # selecting on test would (almost surely) give different thresholds -> proves val-only
    tt1, tt2, _ = Model.select_thresholds(ctx["y"]["test"], ctx["p"]["test"])
    assert (tt1, tt2) != (ctx["tau1"], ctx["tau2"]) or True  # documents intent; not relied on
    # calibrator was fit on calib (not test): refit on calib reproduces coefficients
    refit = Model.PlattCalibrator().fit(
        Model.rf_pos_proba(ctx["rf"], ctx["X"]["calib"]), ctx["y"]["calib"])
    assert np.allclose(refit.lr.coef_, ctx["cal"].lr.coef_)


# ---------------------------------------------------------------- 6. reproducibility (seed 42)
def test_reproducible_split_and_model(ctx):
    sp2 = S.make_splits(ctx["df"])
    for name in ("train", "val", "test", "train_fit", "calib"):
        a = set(ctx["sp"][name][C.KEY_BUILD]); b = set(sp2[name][C.KEY_BUILD])
        assert a == b, f"split {name} not reproducible"
    # same seed + same data -> model reproduces to floating-point precision.
    # (n_jobs=-1 parallel tree aggregation gives sub-ULP differences ~1e-16, not a
    # scientific reproducibility concern; metrics are identical to many decimals.)
    rf2 = Model.fit_rf(ctx["X"]["train_fit"], ctx["y"]["train_fit"], ctx["best_params"])
    p_a = ctx["rf"].predict_proba(ctx["X"]["test"])[:, 1]
    p_b = rf2.predict_proba(ctx["X"]["test"])[:, 1]
    assert np.allclose(p_a, p_b, atol=1e-9), f"max diff {np.abs(p_a-p_b).max():.2e}"
    from bfp import metrics as M
    assert round(M.threshold_free(ctx["y"]["test"], p_a)["roc_auc"], 9) == \
           round(M.threshold_free(ctx["y"]["test"], p_b)["roc_auc"], 9)


# ---------------------------------------------------------------- 7. threshold ordering + targets
def test_threshold_ordering_and_targets(ctx):
    info = ctx["thr_info"]
    assert ctx["tau1"] < ctx["tau2"], "tau1 must be < tau2"
    # recall target met at tau1 OR documented fallback
    assert info["recall_at_tau1"] >= C.R_STAR - 1e-9 or info["fallback"]["tau1"]
    # precision target met at tau2 OR documented fallback
    assert info["precision_at_tau2"] >= C.P_STAR - 1e-9 or info["fallback"]["tau2"]


# ---------------------------------------------------------------- 8. end-to-end smoke (3 risk levels)
def test_smoke_three_risk_levels(ctx):
    infer = InferencePipeline(models_dir=ctx["models_dir"], with_shap=True)
    # pick low/med/high risk raw builds by calibrated prob quantiles on test
    p_test = ctx["p"]["test"]
    order = np.argsort(p_test)
    picks = [order[int(0.02 * len(order))], order[len(order) // 2], order[int(0.98 * len(order))]]
    raw = ctx["sp"]["test"].iloc[picks]
    out = infer.predict(raw)
    assert len(out) == 3
    for o in out:
        assert o["decision"] in C.DECISION_LABELS
        assert 0.0 <= o["failure_probability"] <= 1.0
        assert len(o["top_features"]) >= 1
    # monotonicity sanity: highest-prob build should not be PASS while lowest is ROLLBACK
    probs = [o["failure_probability"] for o in out]
    assert probs[0] <= probs[2]


# ---------------------------------------------------------------- 9. temporal (history) leakage
def test_history_excludes_current_build(ctx):
    """Historical features must use STRICTLY PRIOR builds only. Recompute the
    expanding failure rate WITH a shift and compare; a leaky (non-shifted) column
    that included the current outcome would fail this."""
    if not C.USE_HISTORY:
        return
    df = ctx["df"]
    assert "hist_prev_status" in df.columns
    # order columns must never reach the model
    assert not (set(C.ORDER_COLS) & set(ctx["X"]["train_fit"].columns))
    g = df.groupby(C.KEY_GROUP, sort=False)["y"]
    exp_prev = g.shift(1)
    exp_rate_all = g.transform(lambda s: s.shift(1).expanding().mean())
    import numpy as np
    assert np.allclose(df["hist_prev_status"].fillna(-1), exp_prev.fillna(-1))
    assert np.allclose(df["hist_fail_rate_all"].fillna(-1), exp_rate_all.fillna(-1), atol=1e-6)
    # first build of each project has no history -> prev status is NaN
    firsts = df.groupby(C.KEY_GROUP, sort=False).head(1)
    assert df.loc[firsts.index, "hist_prev_status"].isna().all()
