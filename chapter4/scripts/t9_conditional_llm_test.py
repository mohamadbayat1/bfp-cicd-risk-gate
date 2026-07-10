"""Chapter 4, section 4-7: conditional LLM invocation policy test.

Policy (now documented in LLM_PROMPT.md): the analysis layer is only invoked for
WARN and ROLLBACK decisions. A PASS build needs no explanation or remediation -- there
is nothing to act on -- so calling the LLM for it is pure wasted cost/latency on the
common case (roughly 58% of builds in the held-out test set are PASS). This script
proves the gating logic itself (not just the prompt) with one real example of each
decision state, all three sourced from the same real held-out test set for a clean,
consistent 1-PASS / 1-WARN / 1-ROLLBACK comparison:
  - PASS     -> batch example 9  (p=0.1011) -- must be SKIPPED, no hermes call made
  - WARN     -> batch example 4  (p=0.3467) -- real v2 LLM report generated
  - ROLLBACK -> batch example 2  (p=0.5399) -- real v2 LLM report generated
"""
from __future__ import annotations
import json, os, re, subprocess, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, "chapter4", "tables", "4_7_5_conditional_policy_test.md")

MODEL = "nvidia/llama-3.3-nemotron-super-49b-v1.5"
PROVIDER = "NVIDIA NIM"

from t8_llm_prompt_v2_comparison import (  # noqa: E402  (same directory)
    FEATURE_LABELS, risk_margin, render_prompt_v2, call_hermes,
)

BATCH_DIR = os.path.join(ROOT, "chapter4", "tables", "4_7_3_batch20")
CASES = [
    {"decision_expected": "PASS", "file": "example_09_PASS.md"},
    {"decision_expected": "WARN", "file": "example_04_WARN.md"},
    {"decision_expected": "ROLLBACK", "file": "example_02_ROLLBACK.md"},
]


def load_payload(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    json_block = re.search(r"```json\n(.*?)\n```", text, re.S).group(1)
    return json.loads(json_block)


def main():
    sections = ["# 4-7-5 — Conditional LLM invocation policy test\n",
                f"_Generated: {datetime.datetime.now().isoformat(timespec='seconds')}_\n",
                "_Policy: the LLM analysis layer is invoked ONLY for WARN/ROLLBACK decisions. "
                "PASS builds are skipped entirely -- no LLM call is made, by design, not just "
                "by omission. All 3 cases below are real held-out test-set builds "
                "(`chapter4/tables/4_7_3_batch20/`), one of each decision state._\n"]

    for case in CASES:
        path = os.path.join(BATCH_DIR, case["file"])
        payload = load_payload(path)
        decision = payload["decision"]
        assert decision == case["decision_expected"], f"expected {case['decision_expected']}, got {decision}"

        sections.append(f"## {case['file']} — decision: {decision}\n")

        if decision == "PASS":
            sections.append("**Gate result: SKIPPED.** Decision is PASS -> no LLM call made "
                             "(policy: only WARN/ROLLBACK trigger the analysis layer). "
                             f"Calibrated failure probability was {payload['failure_probability']:.4f}, "
                             f"well under tau1 -- nothing to explain or remediate.\n")
            continue

        prompt, margin = render_prompt_v2(
            decision, payload["thresholds"]["tau1"], payload["thresholds"]["tau2"],
            payload["failure_probability"], payload["top_features"])
        print(f"--- gate triggered for {case['file']} (decision={decision}), calling hermes ---", flush=True)
        response = call_hermes(prompt)

        sections.append(f"**Gate result: TRIGGERED** (risk margin: {margin}). "
                         f"p(fail)={payload['failure_probability']:.4f}.\n")
        sections.append("### LLM-generated report (v2 prompt)\n")
        sections.append(response + "\n")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(sections) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
