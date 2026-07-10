"""Compiles chapter4/tables/4_7_3_batch20_summary.md from whatever example_*.md
files actually exist in chapter4/tables/4_7_3_batch20/ (the batch script crashed on
a hermes timeout partway through -- this compiles from the N that succeeded rather
than assuming all 20)."""
from __future__ import annotations
import glob, json, os, re, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DETAIL_DIR = os.path.join(ROOT, "chapter4", "tables", "4_7_3_batch20")
OUT = os.path.join(ROOT, "chapter4", "tables", "4_7_3_batch20_summary.md")


def parse_file(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    header = re.search(r"decision (\w+), actual (\w+) \(([\w-]+)\)", text)
    decision, actual, correctness = header.group(1), header.group(2), header.group(3)
    json_block = re.search(r"```json\n(.*?)\n```", text, re.S).group(1)
    payload = json.loads(json_block)
    return {
        "n": int(re.search(r"example_(\d+)_", os.path.basename(path)).group(1)),
        "decision": decision, "actual": actual, "correctness": correctness,
        "probability": payload["failure_probability"],
        "top_feature": payload["top_features"][0]["feature"],
    }


def main():
    files = sorted(glob.glob(os.path.join(DETAIL_DIR, "example_*.md")))
    rows = [parse_file(f) for f in files]
    rows.sort(key=lambda r: r["n"])

    lines = ["# 4-7-3 — Batch LLM evaluation on real held-out test builds\n",
             f"_Generated: {datetime.datetime.now().isoformat(timespec='seconds')}_\n",
             f"_{len(rows)} of 20 planned examples completed (the run was stopped after a "
             f"180s timeout on a Hermes call for example 14; {len(rows)} real, complete "
             f"examples were judged sufficient for this qualitative pass). Model: "
             f"`nvidia/llama-3.3-nemotron-super-49b-v1.5` via NVIDIA NIM (Hermes CLI, "
             f"one-shot). Sampled from the real 138,669-build held-out test split; ground "
             f"truth (actual pass/fail) was NOT given to the model or the LLM -- shown "
             f"here only to assess correctness after the fact._\n",
             "| # | Decision | p(fail) | Actual | Match | Top feature |",
             "|---|---|---|---|---|---|"]
    for row in rows:
        lines.append(f"| {row['n']} | {row['decision']} | {row['probability']:.4f} | "
                      f"{row['actual']} | {row['correctness']} | {row['top_feature']} |")

    counts = {}
    for row in rows:
        counts[row["correctness"]] = counts.get(row["correctness"], 0) + 1
    dec_counts = {}
    for row in rows:
        dec_counts[row["decision"]] = dec_counts.get(row["decision"], 0) + 1

    lines.append("")
    lines.append(f"_Decision distribution: {dec_counts}_")
    lines.append(f"_Correctness breakdown: {counts}_")
    lines.append("")
    lines.append("Full input+LLM output for each example: `4_7_3_batch20/example_NN_DECISION.md`")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {OUT} ({len(rows)} examples)")


if __name__ == "__main__":
    main()
