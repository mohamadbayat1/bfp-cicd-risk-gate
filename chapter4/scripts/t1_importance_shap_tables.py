"""Chapter 4, section 4-4-3: top-10 RF importance / top-8 TreeSHAP tables.

Pure trim/format of artifacts/feature_importances.json and artifacts/shap_summary.json.
No recomputation.
"""
from __future__ import annotations
import json, os, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def write_table(path, title, rows, value_key, value_label):
    lines = [f"# {title}\n", f"_Generated: {datetime.datetime.now().isoformat(timespec='seconds')}_\n",
             f"| Rank | Feature | {value_label} |", "|---|---|---|"]
    for i, r in enumerate(rows, 1):
        lines.append(f"| {i} | {r['feature']} | {r[value_key]:.4f} |")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {path}")


def main():
    out_dir = os.path.join(ROOT, "chapter4", "tables")
    os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(ROOT, "artifacts", "feature_importances.json")) as f:
        imp = json.load(f)
    write_table(os.path.join(out_dir, "4_4_3_top10_rf_importance.md"),
                "4-4-3 — Top 10 features by RF importance",
                imp[:10], "importance", "RF importance")

    with open(os.path.join(ROOT, "artifacts", "shap_summary.json")) as f:
        shp = json.load(f)
    write_table(os.path.join(out_dir, "4_4_3_top8_shap.md"),
                "4-4-3 — Top 8 features by mean |TreeSHAP|",
                shp[:8], "mean_abs_shap", "mean |SHAP|")


if __name__ == "__main__":
    main()
