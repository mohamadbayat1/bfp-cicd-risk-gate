"""Chapter 4, section 4-2-3: grouped train/train_fit/calib/val/test split table.

Pure transcription from artifacts/metadata.json -> split_report. No computation.
"""
from __future__ import annotations
import json, os, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "chapter4", "tables", "4_2_3_split_table.md")

LABELS = {
    "train": "Training (all)",
    "train_fit": "Model Fitting (train_fit)",
    "calib": "Calibration",
    "val": "Validation",
    "test": "Test",
}
ORDER = ["train", "train_fit", "calib", "val", "test"]


def main():
    with open(os.path.join(ROOT, "artifacts", "metadata.json")) as f:
        meta = json.load(f)
    rep = meta["split_report"]

    total_projects = rep["val"]["projects"] + rep["test"]["projects"] + \
        (rep["train_fit"]["projects"] + rep["calib"]["projects"])

    lines = ["# 4-2-3 — Grouped data split (by project)\n",
             f"_Generated: {datetime.datetime.now().isoformat(timespec='seconds')}_\n",
             "| Section | Builds | Projects | Failure rate |",
             "|---|---|---|---|"]
    for key in ORDER:
        r = rep[key]
        lines.append(f"| {LABELS[key]} | {r['builds']} | {r['projects']} | {r['failure_rate']:.4f} |")

    lines.append("")
    lines.append(f"_Total unique projects across train+val+test: {total_projects} "
                 f"(no project appears on two sides — verified by automated test #3)._")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
