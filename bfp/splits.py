"""Project-grouped train/val/test split + a grouped calibration carve.

Rows are successive builds of the same project, so a random split would leak
project identity across train/test. We split by `gh_project_name` so no project
appears on two sides. Stratification is approximate (impossible to make exact
with grouping); class ratios are reported and verified close. Deterministic with
SEED -> verification test #6 (reproducibility) and #3 (no project overlap).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit
from . import config as C


def _grouped_split(df: pd.DataFrame, groups: pd.Series, frac: float, seed: int):
    gss = GroupShuffleSplit(n_splits=1, test_size=frac, random_state=seed)
    big_idx, small_idx = next(gss.split(df, groups=groups))
    return df.iloc[big_idx], df.iloc[small_idx]


def make_splits(df: pd.DataFrame, seed: int = C.SEED) -> dict:
    """Return dict of DataFrames: train, train_fit, calib, val, test (each carries
    keys, raw features, y). Splits are grouped by project at every level."""
    g = df[C.KEY_GROUP]
    # 1) carve TEST off everything
    trainval, test = _grouped_split(df, g, C.SPLIT_TEST_FRAC, seed)
    # 2) carve VAL off the remainder (adjust frac to the remainder size)
    val_frac_adj = C.SPLIT_VAL_FRAC / (1.0 - C.SPLIT_TEST_FRAC)
    train, val = _grouped_split(trainval, trainval[C.KEY_GROUP], val_frac_adj, seed)
    # 3) carve CALIBRATION subset off TRAIN (grouped) -> train_fit + calib
    train_fit, calib = _grouped_split(train, train[C.KEY_GROUP], C.CALIB_FRAC_OF_TRAIN, seed)

    splits = {"train": train, "train_fit": train_fit, "calib": calib,
              "val": val, "test": test}
    return {k: v.reset_index(drop=True) for k, v in splits.items()}


def split_report(splits: dict) -> dict:
    rep = {}
    for name, d in splits.items():
        rep[name] = {
            "builds": int(len(d)),
            "projects": int(d[C.KEY_GROUP].nunique()),
            "failure_rate": float(d["y"].mean()),
        }
    return rep


def assert_no_group_overlap(splits: dict):
    """Verification helper (#3): no project shared across train/val/test."""
    sets = {n: set(splits[n][C.KEY_GROUP].unique()) for n in ("train", "val", "test")}
    overlaps = {
        "train&val": sets["train"] & sets["val"],
        "train&test": sets["train"] & sets["test"],
        "val&test": sets["val"] & sets["test"],
    }
    bad = {k: len(v) for k, v in overlaps.items() if v}
    assert not bad, f"PROJECT LEAKAGE across splits: {bad}"
    return True
