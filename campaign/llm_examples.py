"""Generate the campaign's 2 LLM worked examples (1 WARN + 1 ROLLBACK).

Reuses the production prompt workflow (same FEATURE_LABELS,
risk_margin, render_prompt_v2, call_hermes) on two real, scored, true-positive
campaign builds. Categorical feature values are decoded to their original string
labels via the saved preprocessor (the LLM_PROMPT.md rule). Output: one md file per
example in campaign/results/llm_examples/.
"""
from __future__ import annotations
import csv
import io
import json
import os
import sys
import zipfile
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "campaign"))
sys.path.insert(0, os.path.join(ROOT, "chapter4", "scripts"))
sys.path.insert(0, os.path.join(ROOT, "demo-app"))

from orchestrate import gh_download, gh_user  # noqa: E402
from t8_llm_prompt_v2_comparison import (  # noqa: E402
    render_prompt_v2, call_hermes,
)
import joblib  # noqa: E402

# (repo, seq) -> chosen real true-positive builds (see runs.csv)
CASES = [
    {"repo": "bfp-campaign-07", "seq": 32, "expect": "WARN"},
    {"repo": "bfp-campaign-10", "seq": 22, "expect": "ROLLBACK"},
]
OUT_DIR = os.path.join(ROOT, "campaign", "results", "llm_examples")


def row_for(repo: str, seq: int) -> dict:
    with open(os.path.join(ROOT, "campaign", "results", "runs.csv"),
              newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["repo"] == repo and int(r["seq"]) == seq:
                return r
    raise KeyError((repo, seq))


def artifact_result(owner: str, repo: str, run_id: str) -> dict:
    arts = json.loads(gh_download(f"/repos/{owner}/{repo}/actions/runs/{run_id}/artifacts"))
    art = next(a for a in arts["artifacts"] if a["name"] == "risk-gate-report")
    blob = gh_download(f"/repos/{owner}/{repo}/actions/artifacts/{art['id']}/zip")
    zf = zipfile.ZipFile(io.BytesIO(blob))
    with zf.open("risk_gate_result.json") as f:
        return json.load(f)


def decode_categoricals(top_features: list[dict]) -> list[dict]:
    pre = joblib.load(os.path.join(ROOT, "demo-app", "models", "preprocessor.joblib"))
    out = []
    for f in top_features:
        f = dict(f)
        cmap = pre.cat_maps_.get(f["feature"])
        if cmap:
            inverse = {v: k for k, v in cmap.items()}
            f["value"] = inverse.get(int(f["value"]), f["value"])
        out.append(f)
    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    owner = gh_user()
    for case in CASES:
        r = row_for(case["repo"], case["seq"])
        assert r["decision"] == case["expect"], (r["decision"], case)
        res = artifact_result(owner, case["repo"], r["run_id"])
        feats = decode_categoricals(res["top_features"])
        prompt, margin = render_prompt_v2(
            res["decision"], res["thresholds"]["tau1"], res["thresholds"]["tau2"],
            res["failure_probability"], feats)
        print(f"--- calling model for {case['repo']} #{case['seq']} "
              f"({res['decision']}, p={res['failure_probability']:.4f}) ---", flush=True)
        response = None
        for attempt in range(2):
            try:
                response = call_hermes(prompt)
                break
            except Exception as e:
                print(f"  attempt {attempt+1} failed: {e}", flush=True)
        if response is None:
            raise SystemExit("model call failed twice — rerun later")

        payload = {"build": f"{case['repo']} commit #{case['seq']}",
                   "decision": res["decision"],
                   "failure_probability": res["failure_probability"],
                   "thresholds": res["thresholds"],
                   "risk_margin": margin,
                   "top_features": feats,
                   "actual_outcome": "test suite FAILED" if r["label_fail"] == "1" else "tests passed"}
        name = f"example_{res['decision']}_{case['repo']}_{case['seq']:03d}.md"
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as f:
            f.write(f"# Campaign LLM example — {res['decision']} "
                    f"({case['repo']} commit #{case['seq']})\n\n"
                    f"_Generated {datetime.now(timezone.utc).isoformat()} — real scored campaign build; "
                    f"true positive (the build genuinely failed). Generated with the production prompt (see LLM_PROMPT.md)._\n\n"
                    f"## Input payload (real, categoricals decoded)\n\n```json\n"
                    f"{json.dumps(payload, indent=2)}\n```\n\n"
                    f"## LLM-generated report (verbatim)\n\n{response}\n")
        print(f"  saved -> {name}", flush=True)


if __name__ == "__main__":
    main()
