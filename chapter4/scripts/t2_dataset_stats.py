"""Chapter 4, section 4-2-2: dataset overview table + two figures (Tier 2 - light regen).

Reads ONLY 4 raw columns (tr_build_id, gh_project_name, tr_status, gh_lang) from the
full final-2017.csv in chunks, replicating the same contiguous-run dedup logic as
bfp/data.py (so the build count matches exactly), but keeping the raw 4-way
`tr_status` and `gh_lang` values that bfp.data.load_builds() drops. This is a
standalone read (not a retrain) -- ~4 columns instead of the full 26-column feature
set used for training.
"""
from __future__ import annotations
import os, sys, datetime
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from bfp import config as C  # noqa: E402

TABLE_OUT = os.path.join(ROOT, "chapter4", "tables", "4_2_2_dataset_overview.md")
FIG_CLASS = os.path.join(ROOT, "chapter4", "figures", "4_2_2_class_balance_4way.png")
FIG_LANG = os.path.join(ROOT, "chapter4", "figures", "4_2_2_failure_rate_by_language.png")

COLS = [C.KEY_BUILD, C.KEY_GROUP, C.TARGET_RAW, "gh_lang"]


def main():
    os.makedirs(os.path.dirname(TABLE_OUT), exist_ok=True)

    reader = pd.read_csv(C.RAW_CSV, usecols=COLS, dtype=str, na_values=["NA", ""],
                          keep_default_na=True, chunksize=300_000, engine="c")
    kept, raw_rows, last_bid = [], 0, None
    for ch in reader:
        raw_rows += len(ch)
        bid = ch[C.KEY_BUILD]
        prev = bid.shift(1)
        if last_bid is not None and len(prev):
            prev.iloc[0] = last_bid
        ch = ch[bid != prev]
        kept.append(ch)
        if len(bid):
            last_bid = bid.iloc[-1]
    df = pd.concat(kept, ignore_index=True)
    df = df.dropna(subset=[C.KEY_BUILD, C.TARGET_RAW])
    df = df.drop_duplicates(subset=[C.KEY_GROUP, C.KEY_BUILD], keep="first")

    n_builds_all_status = len(df)
    status_counts = df[C.TARGET_RAW].value_counts()

    df_modeled = df[~df[C.TARGET_RAW].isin(C.DROP_STATUS)].copy()
    df_modeled["y"] = (df_modeled[C.TARGET_RAW] != C.PASS_LABEL).astype(int)
    n_modeled = len(df_modeled)
    n_pos = int(df_modeled["y"].sum())
    n_neg = n_modeled - n_pos
    failure_rate = n_pos / n_modeled
    n_projects = df_modeled[C.KEY_GROUP].nunique()

    lang_stats = (df_modeled.groupby("gh_lang")["y"]
                  .agg(["mean", "count"]).sort_values("count", ascending=False))

    # ---------------------------------------------------------------- table
    lines = ["# 4-2-2 — Dataset overview\n",
             f"_Generated: {datetime.datetime.now().isoformat(timespec='seconds')}_\n",
             "| Quantity | Value |", "|---|---|",
             f"| Raw records (job level) | {raw_rows} |",
             f"| Builds after aggregation (before dropping `started`) | {n_builds_all_status} |",
             f"| Builds after dropping `started` (modeled set) | {n_modeled} |",
             f"| Failed builds (y=1: failed/errored/canceled) | {n_pos} |",
             f"| Successful builds (y=0: passed) | {n_neg} |",
             f"| Failure rate | {failure_rate:.4f} |",
             f"| Number of projects | {n_projects} |",
             "",
             "## Build status breakdown (4-way, raw `tr_status`)\n",
             "| Status | Builds | Share |", "|---|---|---|"]
    for status, count in status_counts.items():
        lines.append(f"| {status} | {count} | {count / n_builds_all_status:.4%} |")

    lines += ["", "## Failure rate by language (`gh_lang`)\n",
              "| Language | Builds | Failure rate |", "|---|---|---|"]
    for lang, row in lang_stats.iterrows():
        lines.append(f"| {lang} | {int(row['count'])} | {row['mean']:.4f} |")

    with open(TABLE_OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {TABLE_OUT}")

    # ---------------------------------------------------------------- figures
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.bar(status_counts.index.astype(str), status_counts.values, color="slategray")
    ax.set_ylabel("builds"); ax.set_title("Build status distribution (4-way)")
    fig.tight_layout(); fig.savefig(FIG_CLASS, dpi=120); plt.close(fig)
    print(f"wrote {FIG_CLASS}")

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.bar(lang_stats.index.astype(str), lang_stats["mean"].values, color="indianred")
    ax.set_ylabel("failure rate"); ax.set_title("Failure rate by language")
    fig.tight_layout(); fig.savefig(FIG_LANG, dpi=120); plt.close(fig)
    print(f"wrote {FIG_LANG}")


if __name__ == "__main__":
    main()
