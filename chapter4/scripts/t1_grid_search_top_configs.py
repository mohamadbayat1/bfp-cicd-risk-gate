"""Chapter 4, section 4-3-2: top grid-search configurations (table + chart).

Reads the full 24-candidate CV table already saved in artifacts/grid_search.json.
No retraining, no recomputation of scores -- only sorting/formatting/plotting.
"""
from __future__ import annotations
import json, os, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

TABLE_OUT = os.path.join(ROOT, "chapter4", "tables", "4_3_2_grid_search_top_configs.md")
FIG_OUT = os.path.join(ROOT, "chapter4", "figures", "4_3_2_grid_search_top_configs.png")
TOP_N = 8


def main():
    os.makedirs(os.path.dirname(TABLE_OUT), exist_ok=True)
    os.makedirs(os.path.dirname(FIG_OUT), exist_ok=True)

    with open(os.path.join(ROOT, "artifacts", "grid_search.json")) as f:
        gs = json.load(f)
    results = sorted(gs["search_summary"]["cv_results"], key=lambda r: r["rank"])
    top = results[:TOP_N]

    lines = ["# 4-3-2 — Top grid-search configurations\n",
             f"_Generated: {datetime.datetime.now().isoformat(timespec='seconds')}_\n",
             f"_Full 24-candidate table: `artifacts/grid_search.json`. "
             f"Search: {gs['search_summary']['cv']}, scoring={gs['search_summary']['scoring']}, "
             f"subsample n={gs['search_summary']['search_subsample_n']}._\n",
             "| Rank | max_depth | max_features | min_samples_leaf | n_estimators | "
             "mean CV F-beta | std |",
             "|---|---|---|---|---|---|---|"]
    for r in top:
        p = r["params"]
        lines.append(f"| {r['rank']} | {p['max_depth']} | {p['max_features']} | "
                      f"{p['min_samples_leaf']} | {p['n_estimators']} | "
                      f"{r['mean_test_score']:.4f} | {r['std_test_score']:.4f} |")
    with open(TABLE_OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {TABLE_OUT}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [f"#{r['rank']}: leaf={r['params']['min_samples_leaf']}, "
              f"depth={r['params']['max_depth']}, mf={r['params']['max_features']}, "
              f"n={r['params']['n_estimators']}" for r in top][::-1]
    scores = [r["mean_test_score"] for r in top][::-1]
    stds = [r["std_test_score"] for r in top][::-1]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(labels, scores, xerr=stds, color="steelblue")
    ax.set_xlabel("Mean CV F-beta (beta=2)")
    ax.set_title(f"Top {TOP_N} grid-search configurations (StratifiedGroupKFold)")
    fig.tight_layout()
    fig.savefig(FIG_OUT, dpi=120)
    plt.close(fig)
    print(f"wrote {FIG_OUT}")


if __name__ == "__main__":
    main()
