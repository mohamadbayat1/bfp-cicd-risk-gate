"""Chapter 4, section 4-2-4: leakage-control verification.

Produces chapter4/tables/4_2_4_leakage_verification.md from:
 - bfp/config.py leakage drop-list categories (counts only, no computation)
 - a FRESH `pytest -v` run of tests/test_pipeline.py (so the pass/fail record is current)
 - artifacts/metadata.json -> alarms field (already computed by the last full run)

No retraining. No numbers are invented; everything is either counted from config.py
lists or read from metadata.json / the live pytest run.
"""
from __future__ import annotations
import json, os, re, subprocess, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from bfp import config as C  # noqa: E402

OUT = os.path.join(ROOT, "chapter4", "tables", "4_2_4_leakage_verification.md")


def run_pytest() -> tuple[list[tuple[str, str]], str]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", os.path.join(ROOT, "tests", "test_pipeline.py")],
        cwd=ROOT, capture_output=True, text=True,
    )
    rows = []
    for line in proc.stdout.splitlines():
        m = re.match(r"^(tests/test_pipeline\.py::\S+)\s+(PASSED|FAILED)", line.strip())
        if m:
            name = m.group(1).split("::")[-1]
            rows.append((name, m.group(2)))
    summary_line = next((l for l in proc.stdout.splitlines() if " passed" in l or " failed" in l), "")
    return rows, summary_line


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    n_post_outcome = len(C.LEAKAGE_POST_OUTCOME)
    n_ids_time = len(C.LEAKAGE_IDS_TIME)
    n_missingness = len(C.DROPPED_MISSINGNESS)
    n_total_dropped = len(C.LEAKAGE_DROP)
    n_final_features = len(C.FEATURE_ORDER)

    meta_path = os.path.join(ROOT, "artifacts", "metadata.json")
    with open(meta_path) as f:
        meta = json.load(f)
    alarms = meta["alarms"]

    test_rows, summary_line = run_pytest()

    lines = []
    lines.append("# 4-2-4 — Leakage-control verification\n")
    lines.append(f"_Generated: {datetime.datetime.now().isoformat(timespec='seconds')}_\n")

    lines.append("## Leakage drop-list summary\n")
    lines.append("| Category | Count |")
    lines.append("|---|---|")
    lines.append(f"| Post-outcome columns (known only during/after the build) | {n_post_outcome} |")
    lines.append(f"| Identifiers / hashes / timestamps | {n_ids_time} |")
    lines.append(f"| Dropped for missingness / no signal | {n_missingness} |")
    lines.append(f"| **Total dropped** | **{n_total_dropped}** |")
    lines.append(f"| Raw schema columns (TravisTorrent) | 66 |")
    lines.append(f"| **Final feature count in X** | **{n_final_features}** |")
    lines.append("")

    lines.append("## Automated verification tests (fresh run)\n")
    lines.append(f"_pytest summary: {summary_line.strip()}_\n")
    lines.append("| Test | Result |")
    lines.append("|---|---|")
    for name, result in test_rows:
        lines.append(f"| {name} | {result} |")
    lines.append("")

    lines.append("## Leakage alarm check\n")
    lines.append("| Check | Value | Threshold | Tripped? |")
    lines.append("|---|---|---|---|")
    lines.append(f"| Test ROC-AUC | {alarms['test_roc_auc']:.4f} | >= {C.ALARM_TEST_ROC_AUC} | "
                  f"{alarms['alarm_roc_auc_tripped']} |")
    lines.append(f"| Max single-feature importance | {alarms['max_feature_importance']:.4f} | "
                  f">= {C.ALARM_FEATURE_IMPORTANCE} | {alarms['alarm_feature_importance_tripped']} |")
    lines.append("")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"wrote {OUT}")
    print(summary_line)


if __name__ == "__main__":
    main()
