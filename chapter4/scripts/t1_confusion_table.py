"""Chapter 4, section 4-4-2: three-state decision confusion table + derived rates.

The figure already exists (artifacts/three_state_confusion_test.png, raw counts only).
This adds the table AND the derived operating-characteristic rates that are NOT visible
in the figure (ROLLBACK precision, % of real failures flagged, false-pass rate) --
simple arithmetic on artifacts/metrics.json, no new computation of the underlying counts.
"""
from __future__ import annotations
import json, os, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "chapter4", "tables", "4_4_2_three_state_confusion.md")


def main():
    with open(os.path.join(ROOT, "artifacts", "metrics.json")) as f:
        m = json.load(f)
    cm = m["test"]["three_state_confusion"]
    ap, af = cm["actual_pass"], cm["actual_fail"]
    n_pass = sum(ap.values())
    n_fail = sum(af.values())
    n_total = n_pass + n_fail

    rollback_precision = af["ROLLBACK"] / (af["ROLLBACK"] + ap["ROLLBACK"])
    failures_flagged = (af["WARN"] + af["ROLLBACK"]) / n_fail
    missed_failures_share = af["PASS"] / n_fail
    n_pass_decisions = ap["PASS"] + af["PASS"]
    false_pass_rate = af["PASS"] / n_pass_decisions

    lines = ["# 4-4-2 — Three-state decision confusion (test set)\n",
             f"_Generated: {datetime.datetime.now().isoformat(timespec='seconds')}_\n",
             "| Actual \\ Decision | PASS | WARN | ROLLBACK | Total |",
             "|---|---|---|---|---|",
             f"| Actual pass (n={n_pass}) | {ap['PASS']} | {ap['WARN']} | {ap['ROLLBACK']} | {n_pass} |",
             f"| Actual fail (n={n_fail}) | {af['PASS']} | {af['WARN']} | {af['ROLLBACK']} | {n_fail} |",
             "",
             "## Derived operating characteristics\n",
             "| Metric | Value |", "|---|---|",
             f"| ROLLBACK precision (of builds sent to ROLLBACK, share that really failed) | {rollback_precision:.4f} |",
             f"| Failures flagged (WARN+ROLLBACK as share of all real failures) | {failures_flagged:.4f} |",
             f"| Missed failures (real failures sent to PASS, as share of all real failures) | {missed_failures_share:.4f} |",
             f"| False-pass rate (real failures as share of all PASS decisions) | {false_pass_rate:.4f} |"]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
