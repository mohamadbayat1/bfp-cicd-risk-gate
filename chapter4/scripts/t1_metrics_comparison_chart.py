"""Chapter 4, section 4-4-1: cross-split metrics comparison chart.

Reads artifacts/metrics.json (train/val/test, already computed by run_offline.py)
and plots a grouped bar chart. No recomputation.
"""
from __future__ import annotations
import json, os, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIG_OUT = os.path.join(ROOT, "chapter4", "figures", "4_4_1_metrics_comparison.png")
TABLE_OUT = os.path.join(ROOT, "chapter4", "tables", "4_4_1_metrics_by_split.md")

SPLIT_LABELS = {"train_fit": "Training", "val": "Validation", "test": "Test"}


def main():
    os.makedirs(os.path.dirname(FIG_OUT), exist_ok=True)
    with open(os.path.join(ROOT, "artifacts", "metrics.json")) as f:
        m = json.load(f)

    splits = ["train_fit", "val", "test"]
    metrics = ["roc_auc", "pr_auc", "brier"]
    at_tau1 = ["precision", "recall", "f1", "mcc"]

    lines = ["# 4-4-1 — Model performance across splits\n",
             f"_Generated: {datetime.datetime.now().isoformat(timespec='seconds')}_\n",
             "| Split | ROC-AUC | PR-AUC | Brier | Precision@t1 | Recall@t1 | F1@t1 | MCC@t1 |",
             "|---|---|---|---|---|---|---|---|"]
    data_free = {}
    data_tau1 = {}
    for s in splits:
        tf = m[s]["threshold_free"]
        bt = m[s]["binary_at_tau1"]
        data_free[s] = tf
        data_tau1[s] = bt
        lines.append(f"| {SPLIT_LABELS[s]} | {tf['roc_auc']:.4f} | {tf['pr_auc']:.4f} | "
                      f"{tf['brier']:.4f} | {bt['precision']:.4f} | {bt['recall']:.4f} | "
                      f"{bt['f1']:.4f} | {bt['mcc']:.4f} |")
    with open(TABLE_OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {TABLE_OUT}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    chart_metrics = ["roc_auc", "pr_auc", "f1", "mcc"]
    x = np.arange(len(chart_metrics))
    width = 0.25
    fig, ax = plt.subplots(figsize=(7, 5))
    for i, s in enumerate(splits):
        vals = [data_free[s][k] if k in data_free[s] else data_tau1[s][k] for k in chart_metrics]
        ax.bar(x + (i - 1) * width, vals, width, label=SPLIT_LABELS[s])
    ax.set_xticks(x)
    ax.set_xticklabels(["ROC-AUC", "PR-AUC", "F1@t1", "MCC@t1"])
    ax.set_ylim(0, 1)
    ax.set_title("Key metrics across train / validation / test")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_OUT, dpi=120)
    plt.close(fig)
    print(f"wrote {FIG_OUT}")


if __name__ == "__main__":
    main()
