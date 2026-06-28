"""Data loading and cleaning.

Reads only the needed columns from the large CSV, coerces types, deduplicates to
one row per build, builds the binary target, and drops in-progress builds. No
feature whose value is known only during/after the build is read into the frame
(see config.USECOLS / config.LEAKAGE_DROP).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import config as C

NA_TOKENS = ["NA", ""]


def load_builds(max_rows: int | None = None, chunksize: int = 300_000,
                verbose: bool = False) -> pd.DataFrame:
    """Return a build-level DataFrame: keys + raw features + binary target `y`.

    `max_rows` limits the number of *job-rows* read (for fast tests). Because
    projects are interleaved in the file, even a small prefix spans many projects.

    Memory-safe: job-rows of one build are contiguous, so we drop consecutive
    duplicate build ids while streaming (collapsing ~3.9M job-rows -> ~0.93M
    builds with low RAM), then a final drop_duplicates guarantees correctness for
    any non-contiguous repeats.
    """
    kept = []
    read = 0
    last_bid = None
    reader = pd.read_csv(
        C.RAW_CSV, usecols=C.USECOLS, dtype=str, na_values=NA_TOKENS,
        keep_default_na=True, chunksize=chunksize, engine="c",
    )
    for ch in reader:
        if max_rows is not None and read + len(ch) > max_rows:
            ch = ch.iloc[: max_rows - read]
        read += len(ch)
        bid = ch[C.KEY_BUILD]
        prev = bid.shift(1)
        if last_bid is not None and len(prev):
            prev.iloc[0] = last_bid
        ch = ch[bid != prev]                       # keep first row of each build run
        kept.append(ch)
        if len(bid):
            last_bid = bid.iloc[-1]
        if verbose:
            print(f"  read {read} job-rows", flush=True)
        if max_rows is not None and read >= max_rows:
            break
    df = pd.concat(kept, ignore_index=True)

    # drop rows with no build id or no status (unusable)
    df = df.dropna(subset=[C.KEY_BUILD, C.TARGET_RAW])

    # final safety dedup (catches any non-contiguous repeats)
    df = df.drop_duplicates(subset=[C.KEY_GROUP, C.KEY_BUILD], keep="first")

    # drop in-progress builds (outcome unknown)
    df = df[~df[C.TARGET_RAW].isin(C.DROP_STATUS)].copy()

    # binary target: 0 if passed, 1 otherwise
    df["y"] = (df[C.TARGET_RAW] != C.PASS_LABEL).astype("int8")

    # coerce numeric raw features to float32
    for col in C.FEATURES_NUMERIC:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float32")

    # keep keys + raw features + target only
    keep = [C.KEY_BUILD, C.KEY_GROUP] + C.FEATURES_NUMERIC + C.FEATURES_CATEGORICAL + ["y"]
    df = df[keep].reset_index(drop=True)
    return df


def class_balance(df: pd.DataFrame) -> dict:
    n = len(df)
    pos = int(df["y"].sum())
    return {"n": n, "positives": pos, "negatives": n - pos,
            "failure_rate": pos / n if n else float("nan")}
