"""Campaign scorer (CAMPAIGN_PLAN.md, Phase A5).

Reads campaign/results/runs.csv (written by orchestrate.py), applies the warm-up rule
(builds with fewer than WARMUP prior runs are excluded from metrics), and produces:

  campaign/results/campaign_overview.md   table 1: repos x builds x warm-up/scored x realized failure rate
  campaign/results/online_metrics.md      table 2: ROC-AUC / PR-AUC / Brier + 3-state confusion
                                          (side by side with the offline test row)
  campaign/results/cold_start_curve.png   figure 1: Brier (+ failure rate) vs prior-run bucket
  campaign/results/prob_distribution.png  figure 2 (optional): calibrated p by actual outcome

Decisions are re-derived from the recorded calibrated probability using the SAVED
thresholds (models/thresholds.json), which also cross-checks the decision column the
gate reported live.
"""
from __future__ import annotations
import csv
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "campaign", "results")
CSV_PATH = os.path.join(RESULTS_DIR, "runs.csv")
WARMUP = 20

# offline test row (RESULTS.md section 7) for the side-by-side comparison
OFFLINE = {"roc_auc": 0.8602, "pr_auc": 0.7489, "brier": 0.1105,
           "n": 138669, "fail_rate": 0.2401}


def load_rows() -> list[dict]:
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    usable = []
    for r in rows:
        if r["probability"] in ("", None) or r["label_fail"] in ("", None):
            continue  # dry-run rows / infra failures without a verdict
        if r.get("run_conclusion") not in ("success", "failure"):
            continue
        usable.append({
            "repo": r["repo"], "seq": int(r["seq"]), "commit_type": r["commit_type"],
            "p": float(r["probability"]), "y": int(r["label_fail"]),
            "decision_live": r["decision"],
            "n_prior": int(float(r["n_prior_runs"])) if r["n_prior_runs"] != "" else 0,
        })
    return usable


def thresholds() -> tuple[float, float]:
    with open(os.path.join(ROOT, "models", "thresholds.json")) as f:
        t = json.load(f)
    return float(t["tau1"]), float(t["tau2"])


def decide(p: float, t1: float, t2: float) -> str:
    return "PASS" if p < t1 else ("WARN" if p < t2 else "ROLLBACK")


def metrics(y: np.ndarray, p: np.ndarray) -> dict:
    from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
    out = {"n": len(y), "fail_rate": float(y.mean())}
    if len(np.unique(y)) > 1:
        out["roc_auc"] = float(roc_auc_score(y, p))
        out["pr_auc"] = float(average_precision_score(y, p))
    else:
        out["roc_auc"] = out["pr_auc"] = float("nan")
    out["brier"] = float(brier_score_loss(y, p))
    return out


def main():
    rows = load_rows()
    if not rows:
        raise SystemExit(f"no usable rows in {CSV_PATH}")
    t1, t2 = thresholds()

    scored = [r for r in rows if r["n_prior"] >= WARMUP]
    warm = [r for r in rows if r["n_prior"] < WARMUP]

    # cross-check live decision vs re-derived decision
    mismatches = [r for r in scored if r["decision_live"] and
                  decide(r["p"], t1, t2) != r["decision_live"]]

    # ---------------------------------------------------------- table 1: overview
    repos = sorted({r["repo"] for r in rows})
    lines1 = ["# Campaign overview", "",
              f"_warm-up rule: builds with < {WARMUP} prior runs are excluded from metrics_", "",
              "| Repo | total runs | warm-up | scored | scored failure rate |",
              "|---|---|---|---|---|"]
    for repo in repos:
        rr = [r for r in rows if r["repo"] == repo]
        sc = [r for r in rr if r["n_prior"] >= WARMUP]
        fr = (sum(r["y"] for r in sc) / len(sc)) if sc else float("nan")
        lines1.append(f"| {repo} | {len(rr)} | {len(rr) - len(sc)} | {len(sc)} | {fr:.3f} |")
    fr_all = sum(r["y"] for r in scored) / len(scored) if scored else float("nan")
    lines1.append(f"| **total** | {len(rows)} | {len(warm)} | {len(scored)} | **{fr_all:.3f}** |")

    # ---------------------------------------------------------- table 2: metrics
    y = np.array([r["y"] for r in scored]); p = np.array([r["p"] for r in scored])
    m = metrics(y, p)
    conf = {(a, d): 0 for a in (0, 1) for d in ("PASS", "WARN", "ROLLBACK")}
    for r in scored:
        conf[(r["y"], decide(r["p"], t1, t2))] += 1
    flagged = conf[(1, "WARN")] + conf[(1, "ROLLBACK")]
    n_fail = sum(v for (a, _), v in conf.items() if a == 1)
    rb_total = conf[(0, "ROLLBACK")] + conf[(1, "ROLLBACK")]
    rb_prec = conf[(1, "ROLLBACK")] / rb_total if rb_total else float("nan")
    n_pass_dec = conf[(0, "PASS")] + conf[(1, "PASS")]
    false_pass = conf[(1, "PASS")] / n_pass_dec if n_pass_dec else float("nan")

    lines2 = ["# Online metrics (scored builds, saved thresholds "
              f"tau1={t1:.4f} / tau2={t2:.4f})", "",
              "| setting | n | failure rate | ROC-AUC | PR-AUC | Brier |",
              "|---|---|---|---|---|---|",
              f"| online campaign | {m['n']} | {m['fail_rate']:.4f} | {m['roc_auc']:.4f} | {m['pr_auc']:.4f} | {m['brier']:.4f} |",
              f"| offline held-out test (reference) | {OFFLINE['n']:,} | {OFFLINE['fail_rate']:.4f} | {OFFLINE['roc_auc']:.4f} | {OFFLINE['pr_auc']:.4f} | {OFFLINE['brier']:.4f} |",
              "",
              "## Three-state confusion (actual x decision)",
              "",
              "| actual \\ decision | PASS | WARN | ROLLBACK |",
              "|---|---|---|---|",
              f"| pass (n={conf[(0,'PASS')]+conf[(0,'WARN')]+conf[(0,'ROLLBACK')]}) | {conf[(0,'PASS')]} | {conf[(0,'WARN')]} | {conf[(0,'ROLLBACK')]} |",
              f"| fail (n={n_fail}) | {conf[(1,'PASS')]} | {conf[(1,'WARN')]} | {conf[(1,'ROLLBACK')]} |",
              "",
              f"- ROLLBACK precision: **{rb_prec:.4f}**",
              f"- failures flagged (WARN+ROLLBACK): **{flagged / n_fail:.3f}**" if n_fail else "- failures flagged: n/a",
              f"- false-pass rate (fails inside PASS decisions): **{false_pass:.4f}**",
              "",
              f"_live-vs-rederived decision mismatches: {len(mismatches)}_"]

    # ------------------------------------------------- figure 1: cold-start curve
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    buckets = [(0, 4), (5, 9), (10, 19), (20, 29), (30, 10 ** 9)]
    labels, briers, frates, ns = [], [], [], []
    for lo, hi in buckets:
        bb = [r for r in rows if lo <= r["n_prior"] <= hi]
        if not bb:
            continue
        yy = np.array([r["y"] for r in bb]); pp = np.array([r["p"] for r in bb])
        labels.append(f"{lo}-{'' if hi > 999 else hi}+".replace("-+", "+") if hi > 999 else f"{lo}-{hi}")
        briers.append(float(np.mean((pp - yy) ** 2)))
        frates.append(float(yy.mean()))
        ns.append(len(bb))
    fig, ax = plt.subplots(figsize=(6.5, 4))
    x = np.arange(len(labels))
    ax.bar(x, briers, width=0.6, color="#4472c4", label="Brier (lower = better)")
    ax.plot(x, frates, "o--", color="#c00000", label="actual failure rate")
    for xi, n in zip(x, ns):
        ax.text(xi, 0.005, f"n={n}", ha="center", fontsize=8, color="white")
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_xlabel("prior gate runs available (history depth)")
    ax.set_title("Cold start: prediction quality vs available history")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "cold_start_curve.png"), dpi=150)
    plt.close(fig)

    # -------------------------------------------- figure 2: probability histogram
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.hist(p[y == 0], bins=25, alpha=0.6, label="actual pass", color="#70ad47", density=True)
    ax.hist(p[y == 1], bins=25, alpha=0.6, label="actual fail", color="#c00000", density=True)
    ax.axvline(t1, ls="--", color="orange", label="tau1")
    ax.axvline(t2, ls="--", color="red", label="tau2")
    ax.set_xlabel("calibrated failure probability")
    ax.set_title("Scored online builds: probability by actual outcome")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "prob_distribution.png"), dpi=150)
    plt.close(fig)

    with open(os.path.join(RESULTS_DIR, "campaign_overview.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines1) + "\n")
    with open(os.path.join(RESULTS_DIR, "online_metrics.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines2) + "\n")

    print("\n".join(lines1)); print(); print("\n".join(lines2))
    print("\nfigures ->", RESULTS_DIR)


if __name__ == "__main__":
    main()
