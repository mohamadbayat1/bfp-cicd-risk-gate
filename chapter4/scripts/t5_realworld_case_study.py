"""Chapter 4, section 4-6-5: real-world case study results.

Assembles the ACTUAL results from 5 real GitHub Actions runs (a genuine push per
commit, on https://github.com/novavisionstudio-byte/bfp-cicd-risk-gate-demo) into a
table + figure. Every number here was downloaded from a real workflow-run artifact
(demo-app/ci_gate_runs/commitN/risk_gate_result.json) -- nothing is simulated.

Commit 1's own run is EXCLUDED from this table: it was corrupted by two
infrastructure bugs found and fixed live (a pytest invocation bug, then a
force-push/history edge case) -- see the "infra-failure contamination" note below.
The clean case study genuinely starts at commit 2.
"""
from __future__ import annotations
import json, os, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNS_DIR = os.path.join(ROOT, "demo-app", "ci_gate_runs")
TABLE_OUT = os.path.join(ROOT, "chapter4", "tables", "4_6_5_realworld_case_study.md")
FIG_OUT = os.path.join(ROOT, "chapter4", "figures", "4_6_5_realworld_case_study.png")

COMMITS = [
    {"n": 2, "sha": "35f2bd9", "desc": "Add factorial function with tests", "nature": "clean, tested",
     "actual_tests": "pass"},
    {"n": 3, "sha": "3d53d6f", "desc": "Expose factorial via the API", "nature": "clean, tested",
     "actual_tests": "pass"},
    {"n": 4, "sha": "cd9ddfc", "desc": "Add stats module (large diff, light tests)", "nature": "large diff, weak tests",
     "actual_tests": "pass"},
    {"n": 5, "sha": "c6355d4", "desc": "Handle divide-by-zero by returning 0 (removes the exception)",
     "nature": "small diff, breaks behavior", "actual_tests": "FAIL (2 tests)"},
    {"n": 6, "sha": "28afd94", "desc": "Fix: restore ValueError on divide-by-zero", "nature": "fix",
     "actual_tests": "pass (job skipped -- gate ROLLBACK stopped it first)"},
]


def main():
    rows = []
    for c in COMMITS:
        path = os.path.join(RUNS_DIR, f"commit{c['n']}", "risk_gate_result.json")
        with open(path) as f:
            r = json.load(f)
        rows.append({**c, "result": r})

    lines = ["# 4-6-5 — Real-world GitHub Actions case study (5 real runs)\n",
             f"_Generated: {datetime.datetime.now().isoformat(timespec='seconds')}_\n",
             "_Repo: https://github.com/novavisionstudio-byte/bfp-cicd-risk-gate-demo "
             "-- every row is a real, separately-pushed commit that triggered a real "
             "GitHub Actions run of `.github/workflows/risk-gate.yml`._\n",
             "| # | Commit | Nature | Gate decision | p(fail) | Top SHAP feature | Actual test outcome |",
             "|---|---|---|---|---|---|---|"]
    for row in rows:
        r = row["result"]
        top = r["top_features"][0]
        lines.append(
            f"| {row['n']} | {row['desc']} | {row['nature']} | **{r['decision']}** | "
            f"{r['failure_probability']:.4f} | {top['feature']}={top['value']:.3g} "
            f"(SHAP {top['shap']:+.4f}) | {row['actual_tests']} |")

    lines.append("")
    lines.append(f"_Thresholds: tau1={rows[0]['result']['thresholds']['tau1']:.4f}, "
                  f"tau2={rows[0]['result']['thresholds']['tau2']:.4f}._")
    lines.append("")
    lines.append(
        "**Note on commit 1.** Its own live run is excluded here: two infrastructure "
        "bugs (a `pytest` invocation difference between local and CI, then a "
        "force-push history-resolution edge case) were found and fixed live against "
        "it, and the resulting failed runs transiently *contaminated* the live "
        "history signal (the model correctly, if misleadingly, saw 2 prior "
        "'failures' that were actually my own CI-config bugs, not application risk, "
        "and returned ROLLBACK). Those runs were deleted once the fix landed; the "
        "clean case study begins at commit 2. This is itself a genuine, worth-reporting "
        "finding: transient CI infrastructure failures pollute the live history "
        "features exactly as much as real application failures, until cleaned up.")

    os.makedirs(os.path.dirname(TABLE_OUT), exist_ok=True)
    with open(TABLE_OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {TABLE_OUT}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    xs = [row["n"] for row in rows]
    ps = [row["result"]["failure_probability"] for row in rows]
    colors = ["seagreen" if row["result"]["decision"] == "PASS"
              else "darkorange" if row["result"]["decision"] == "WARN"
              else "firebrick" for row in rows]
    tau1 = rows[0]["result"]["thresholds"]["tau1"]
    tau2 = rows[0]["result"]["thresholds"]["tau2"]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar([str(x) for x in xs], ps, color=colors)
    ax.axhline(tau1, color="green", ls="--", lw=1, label=f"tau1={tau1:.3f}")
    ax.axhline(tau2, color="red", ls="--", lw=1, label=f"tau2={tau2:.3f}")
    ax.set_xlabel("Commit #"); ax.set_ylabel("Calibrated failure probability")
    ax.set_title("Real GitHub Actions runs: gate probability per commit\n"
                  "(commit 5 breaks tests for real; commit 6 is flagged ROLLBACK from real prior-failure history)")
    ax.legend()
    fig.tight_layout()
    os.makedirs(os.path.dirname(FIG_OUT), exist_ok=True)
    fig.savefig(FIG_OUT, dpi=120)
    plt.close(fig)
    print(f"wrote {FIG_OUT}")


if __name__ == "__main__":
    main()
