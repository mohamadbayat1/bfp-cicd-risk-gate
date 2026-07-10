"""Chapter 4, section 4-3-4: selected threshold policy table.

Pure transcription from models/thresholds.json. No computation.
"""
from __future__ import annotations
import json, os, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "chapter4", "tables", "4_3_4_threshold_policy.md")


def main():
    with open(os.path.join(ROOT, "models", "thresholds.json")) as f:
        th = json.load(f)

    lines = ["# 4-3-4 — Selected threshold policy (validation set)\n",
             f"_Generated: {datetime.datetime.now().isoformat(timespec='seconds')}_\n",
             "| Quantity | Value |", "|---|---|",
             f"| tau1 (PASS / WARN boundary) | {th['tau1']:.4f} |",
             f"| tau2 (WARN / ROLLBACK boundary) | {th['tau2']:.4f} |",
             f"| r* (target recall for tau1) | {th['r_star']:.2f} |",
             f"| p* (target precision for tau2) | {th['p_star']:.2f} |",
             f"| Recall@tau1 (validation) | {th['recall_at_tau1']:.4f} |",
             f"| Precision@tau2 (validation) | {th['precision_at_tau2']:.4f} |",
             f"| Fallback used for tau1? | {th['fallback']['tau1']} |",
             f"| Fallback used for tau2? | {th['fallback']['tau2']} |",
             "",
             f"_tau1 < tau2 holds: {th['tau1'] < th['tau2']}. Both recall/precision targets "
             f"were met without a fallback firing, but at the exact boundary of the "
             f"feasible region (Recall@tau1 == r* to 2 decimals) -- see HANDOFF.md's honest "
             f"note on fallback risk._"]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
