"""4-6 header figure: architecture/sequence diagram of the live GitHub Actions
deployment (commit push -> risk-gate job -> live feature extraction -> inference
-> TreeSHAP -> three-state gate -> test job). Purely illustrative (no data),
matching the actual demo-app implementation (ci_gate/extract_features.py,
ci_gate/predict.py, .github/workflows/risk-gate.yml)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "figures" / "4_6_architecture.png"

fig, ax = plt.subplots(figsize=(9.4, 12.8))
ax.set_xlim(0, 10)
ax.set_ylim(0, 17.4)
ax.axis("off")

BOX = dict(boxstyle="round,pad=0.30", linewidth=1.4)

def box(x, y, w, h, title, lines, fc, ec, title_size=11.5, size=9.5):
    p = FancyBboxPatch((x, y), w, h, fc=fc, ec=ec, **BOX)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h - 0.36, title, ha="center", va="center",
            fontsize=title_size, fontweight="bold", color="#1a1a1a")
    if lines:
        ax.text(x + w / 2, y + (h - 0.72) / 2, "\n".join(lines), ha="center",
                va="center", fontsize=size, color="#333333")

def arrow(x1, y1, x2, y2, label=None, color="#444444", ls="-"):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=16,
                        linewidth=1.6, color=color, linestyle=ls)
    ax.add_patch(a)
    if label:
        ax.text((x1 + x2) / 2 + 0.12, (y1 + y2) / 2, label, fontsize=9,
                ha="left", va="center", color=color)

# 1. developer push
box(2.9, 15.95, 4.2, 0.95, "Developer", ["git push  (one commit = one run)"],
    "#eef4fb", "#3a6ea5")
arrow(5.0, 15.62, 5.0, 15.42, "push event")

# 2. GitHub Actions workflow container
box(0.6, 8.05, 8.8, 7.05,
    "GitHub Actions — risk-gate.yml  (job 1: risk gate, runs BEFORE tests)",
    [], "#f7f7f7", "#888888")

# 2a. live feature extraction
box(1.1, 12.35, 7.8, 1.85, "Live feature extraction  (ci_gate/extract_features.py)",
    ["diff features: git diff of the pushed commit (churn, files, tests, sloc)",
     "context features: repo metadata (language, team, PR status)",
     "hist_* features: this repo's own previous gate runs (GitHub REST API,",
     "strictly prior outcomes, shift-by-one — same rule as offline training)"],
    "#fdf6e3", "#b58900")
arrow(5.0, 12.02, 5.0, 11.82, "32-feature vector x")

# 2b. inference / 2c. explainability
box(0.9, 10.0, 4.3, 1.5, "Inference  (ci_gate/predict.py)",
    ["saved preprocessor (encoders, medians)",
     "RandomForest  →  raw score",
     "Platt calibration  →  p(fail)"],
    "#eef7ee", "#2e7d32", size=9)
box(6.5, 10.0, 2.5, 1.5, "TreeSHAP",
    ["per-build feature", "contributions", "(top-k, signed)"],
    "#f3eefb", "#6a4fa3", size=9)
arrow(5.55, 10.75, 6.15, 10.75)

# 2d. decision gate
box(1.1, 8.45, 7.8, 0.65, "Three-state decision gate",
    ["p < τ1 = 0.1119 → PASS      τ1 ≤ p < τ2 → WARN      p ≥ τ2 = 0.4662 → ROLLBACK"],
    "#fff0f0", "#b3403c")
arrow(3.0, 9.67, 3.0, 9.44)
arrow(7.7, 9.67, 7.7, 9.44, "SHAP values")

# outcomes
box(0.6, 6.05, 2.6, 1.3, "PASS", ["gate job succeeds", "(no LLM call —", "skipped by policy)"],
    "#eef7ee", "#2e7d32", size=9)
box(3.7, 6.05, 2.6, 1.3, "WARN", ["gate job succeeds", "+ warning annotation", "+ LLM report"],
    "#fdf6e3", "#b58900", size=9)
box(6.8, 6.05, 2.6, 1.3, "ROLLBACK", ["gate job FAILS", "(pipeline blocked)", "+ LLM report"],
    "#fdeaea", "#b3403c", size=9)
arrow(1.9, 8.12, 1.9, 7.68)
arrow(5.0, 8.12, 5.0, 7.68)
arrow(8.1, 8.12, 8.1, 7.68)

# LLM layer (conditional)
box(3.5, 3.85, 5.9, 1.25, "LLM analysis layer  (WARN / ROLLBACK only)",
    ["payload: decision, p(fail), decoded features + SHAP  →  grounded report",
     "(Summary / Why / What to do / Technical details)"],
    "#f3eefb", "#6a4fa3", size=9)
arrow(5.0, 5.72, 5.6, 5.43, color="#6a4fa3", ls="--")
arrow(8.1, 5.72, 7.7, 5.43, color="#6a4fa3", ls="--")

# test job
box(0.6, 0.7, 4.0, 1.3, "job 2: tests  (needs: risk-gate)",
    ["runs ONLY if the gate did not fail —", "ROLLBACK genuinely skips the tests"],
    "#eef4fb", "#3a6ea5", size=9)
arrow(1.9, 5.72, 1.9, 2.33, "continue")
arrow(3.85, 5.72, 2.75, 2.33)
ax.text(6.9, 1.35, "on ROLLBACK: the test job is skipped\n(real early stop, before tests run)",
        fontsize=9.5, ha="center", va="center", color="#b3403c", style="italic")

fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
print("wrote", OUT)
