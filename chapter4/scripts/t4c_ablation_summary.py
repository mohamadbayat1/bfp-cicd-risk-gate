"""Chapter 4, section 4-5: ablation summary table + figure (the central finding).

Assembles the 3-row ablation table from three independently-produced sources:
  1. artifacts/metrics.json                              -> diff+history, grouped (final model)
  2. chapter4/ablation/diffonly_grouped/artifacts/metrics.json -> diff-only, grouped
  3. chapter4/ablation/diffonly_random/metrics.json       -> diff-only, random (diagnostic)
No numbers are computed here -- pure assembly + plotting.
"""
from __future__ import annotations
import json, os, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TABLE_OUT = os.path.join(ROOT, "chapter4", "tables", "4_5_ablation_summary.md")
FIG_OUT = os.path.join(ROOT, "chapter4", "figures", "4_5_ablation_summary.png")


def main():
    with open(os.path.join(ROOT, "artifacts", "metrics.json")) as f:
        final = json.load(f)["test"]["threshold_free"]

    with open(os.path.join(ROOT, "chapter4", "ablation", "diffonly_grouped",
                            "artifacts", "metrics.json")) as f:
        diffonly_grouped = json.load(f)["test"]["threshold_free"]

    with open(os.path.join(ROOT, "chapter4", "ablation", "diffonly_random",
                            "metrics.json")) as f:
        diffonly_random = json.load(f)

    rows = [
        ("Diff features only, grouped (cross-project)",
         diffonly_grouped["roc_auc"], diffonly_grouped["pr_auc"], diffonly_grouped["brier"],
         "Valid ablation (leakage-free; isolates history's contribution)"),
        ("Diff features only, random (within-project)",
         diffonly_random["roc_auc"], diffonly_random["pr_auc"], None,
         "DIAGNOSTIC — project-identity leakage; NOT a candidate result"),
        ("Diff + history, grouped (cross-project) — FINAL MODEL",
         final["roc_auc"], final["pr_auc"], final["brier"],
         "Final reported model"),
    ]

    lines = ["# 4-5 — Ablation: split strategy and historical features\n",
             f"_Generated: {datetime.datetime.now().isoformat(timespec='seconds')}_\n",
             "| Configuration | ROC-AUC | PR-AUC | Brier | Condition |",
             "|---|---|---|---|---|"]
    for name, roc, pr, brier, cond in rows:
        brier_s = f"{brier:.4f}" if brier is not None else "—"
        lines.append(f"| {name} | {roc:.4f} | {pr:.4f} | {brier_s} | {cond} |")

    ov = diffonly_random["project_overlap"]
    lines.append("")
    lines.append(f"_Random-split project overlap: {ov['overlap_projects']}/{ov['test_projects']} "
                 f"({ov['overlap_pct_of_test_projects']:.1%}) of test-split projects also appear "
                 f"in train under the random split, vs. 0% by construction under the grouped "
                 f"split -- the concrete mechanism behind the gap above._")

    os.makedirs(os.path.dirname(TABLE_OUT), exist_ok=True)
    with open(TABLE_OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {TABLE_OUT}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    labels = ["Diff-only\ngrouped", "Diff-only\nrandom\n(diagnostic)", "Diff+history\ngrouped\n(final)"]
    roc_vals = [r[1] for r in rows]
    pr_vals = [r[2] for r in rows]
    x = np.arange(len(labels)); width = 0.35

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(x - width / 2, roc_vals, width, label="ROC-AUC", color="steelblue")
    ax.bar(x + width / 2, pr_vals, width, label="PR-AUC", color="darkorange")
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    ax.axhline(0.5, color="gray", ls=":", lw=1, label="chance (ROC-AUC=0.5)")
    ax.set_title("Ablation: split strategy and historical features")
    ax.legend()
    fig.tight_layout()
    os.makedirs(os.path.dirname(FIG_OUT), exist_ok=True)
    fig.savefig(FIG_OUT, dpi=120)
    plt.close(fig)
    print(f"wrote {FIG_OUT}")


if __name__ == "__main__":
    main()
