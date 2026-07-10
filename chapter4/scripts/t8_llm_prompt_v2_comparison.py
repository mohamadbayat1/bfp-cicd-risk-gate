"""Chapter 4, section 4-7: developer-facing prompt refinement (v2), with a direct
before/after comparison on the same real payloads.

Fixes, based on reviewing 15 real v1 outputs:
  1. Verbosity/jargon -> a 1-sentence plain-English Summary leads the report; raw
     feature names + exact SHAP numbers move to a "Technical details" appendix.
  2. Raw feature names sometimes leaked into prose -> a static FEATURE_LABELS map
     (code, not LLM guesswork) supplies a plain-English description for every feature;
     the prompt instructs the model to use ONLY the plain description in the reader-
     facing sections.
  3. No confidence calibration -> a computed qualitative "risk margin" (how close p is
     to the relevant threshold) is fed in, with an instruction to temper language near
     a boundary vs. deep in a decision zone.
  4. The one observed completeness slip (an omitted feature) -> explicit "mention every
     provided feature at least once" rule, now checked in Technical details too.

Re-runs the SAME real payloads already used for the v1 examples (commit6 ROLLBACK from
the GitHub demo, and batch example 9 PASS from the held-out test set) through the new
v2 prompt, so the before/after is a fair, direct comparison -- not new/different data.
"""
from __future__ import annotations
import json, os, re, subprocess, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
OUT_DIR = os.path.join(ROOT, "chapter4", "tables")

MODEL = "nvidia/llama-3.3-nemotron-super-49b-v1.5"
PROVIDER = "NVIDIA NIM"

FEATURE_LABELS = {
    "gh_team_size": "number of people who have contributed to this project",
    "git_num_all_built_commits": "number of commits included in this build",
    "gh_num_commit_comments": "number of review comments on this build's commits",
    "git_diff_src_churn": "lines of source code changed",
    "git_diff_test_churn": "lines of test code changed",
    "gh_diff_files_added": "number of new files added",
    "gh_diff_files_deleted": "number of files deleted",
    "gh_diff_files_modified": "number of existing files modified",
    "gh_diff_tests_added": "number of new test files added",
    "gh_diff_tests_deleted": "number of test files deleted",
    "gh_diff_src_files": "number of source-code files changed",
    "gh_diff_doc_files": "number of documentation files changed",
    "gh_diff_other_files": "number of other (non-source, non-doc) files changed",
    "gh_num_commits_on_files_touched": "how often the changed files have been modified historically",
    "gh_sloc": "total codebase size (lines of code)",
    "gh_test_lines_per_kloc": "amount of test code relative to codebase size",
    "gh_test_cases_per_kloc": "number of test cases relative to codebase size",
    "gh_asserts_cases_per_kloc": "number of test assertions relative to codebase size",
    "gh_repo_age": "how long this project has existed",
    "gh_repo_num_commits": "total commits in the project's history",
    "hist_prev_status": "whether the immediately previous build passed or failed",
    "hist_fail_rate_5": "failure rate over the last 5 builds",
    "hist_fail_rate_20": "failure rate over the last 20 builds",
    "hist_fail_rate_all": "failure rate over the project's entire build history",
    "hist_consec_fail": "number of consecutive prior failed builds",
    "hist_build_seq": "number of prior builds this project has had (project maturity)",
    "churn_ratio": "ratio of test-code changes to source-code changes",
    "test_coverage_proxy": "estimated test volume relative to codebase size",
    "gh_lang": "programming language",
    "gh_is_pr": "whether this build is from a pull request",
    "gh_by_core_team_member": "whether the change was made by a core team member",
    "git_prev_commit_resolution_status": "how the previous commit's build history was resolved",
}

SYSTEM_PROMPT_V2 = """You are a CI/CD build-risk assistant writing a short note for a software developer who
has no machine-learning background. You are given a build's pre-build risk assessment:
a three-state decision, a calibrated failure probability, a qualitative risk-margin
description (how close the probability is to the decision boundary), and the features
that most influenced the model -- each with a plain-English description, its raw value,
and its SHAP attribution.

Rules:
- Use ONLY the information provided. Do NOT invent metrics, logs, test names, stack
  traces, or history not present in the input.
- SHAP sign convention: positive SHAP increases failure risk; negative decreases it.
- Write the Summary and Why sections in plain English for a developer -- use the given
  plain-English descriptions, never the internal variable names, and do not put raw
  SHAP numbers in these two sections.
- Calibrate your confidence language to the given risk margin: if it says "just above"
  or "just below" a threshold, use tempered language (slightly/marginally elevated); if
  it says "well above" or "well below", you may be more assertive.
- Mention every provided feature at least once (Why or Technical details) -- do not
  silently omit any.
- Be concise. No filler."""

USER_TEMPLATE_V2 = """Build risk assessment:
- Decision: {decision}
- Calibrated failure probability: {probability}
- Risk margin: {margin}
- Contributing signals (plain description = raw value, SHAP):
{feature_lines}

Produce a report with exactly these four sections:

1. **Summary** (1 sentence, plain English, no variable names or SHAP numbers): what a
   developer glancing at this build needs to know.
2. **Why** (bullet list, plain English): each signal's direction (raises/lowers risk)
   and a one-clause reason, using the plain descriptions given -- no raw variable names
   or SHAP numbers in this section.
3. **What to do** (bullet list, 2-4 items): concrete actions, each tied to a signal above.
4. **Technical details** (compact list): raw feature name, value, and SHAP value for
   every provided signal, for audit/traceability.

Constraints: ground every statement in the provided data; if a section has no support,
write "Insufficient signal in the provided data." Do not add a fifth section."""


def risk_margin(p, tau1, tau2, decision):
    if decision == "PASS":
        frac = (tau1 - p) / tau1 if tau1 > 0 else 1.0
        return ("well below the WARN threshold" if frac > 0.5
                else "just below the WARN threshold")
    if decision == "WARN":
        frac = (p - tau1) / (tau2 - tau1)
        return ("just above the WARN threshold" if frac < 0.33
                else "in the middle of the WARN range" if frac < 0.66
                else "close to the ROLLBACK threshold")
    frac = min(1.0, (p - tau2) / (1 - tau2))
    return ("just above the ROLLBACK threshold" if frac < 0.33
            else "well above the ROLLBACK threshold" if frac < 0.66
            else "very deep into ROLLBACK territory")


def render_prompt_v2(decision, tau1, tau2, probability, top_features):
    margin = risk_margin(probability, tau1, tau2, decision)
    feature_lines = "\n".join(
        f"  - {FEATURE_LABELS.get(f['feature'], f['feature'])} "
        f"[{f['feature']}] = {f['value']}  (SHAP {f['shap']:+.4f})"
        for f in top_features
    )
    user = USER_TEMPLATE_V2.format(decision=decision, probability=probability,
                                    margin=margin, feature_lines=feature_lines)
    return SYSTEM_PROMPT_V2 + "\n\n" + user, margin


def call_hermes(prompt: str) -> str:
    result = subprocess.run(["hermes", "-z", prompt, "--cli"],
                             capture_output=True, text=True, encoding="utf-8", timeout=180)
    if result.returncode != 0:
        raise RuntimeError(f"hermes call failed: {result.stderr}")
    return result.stdout.strip()


def load_v1_payload_and_response(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    json_block = re.search(r"```json\n(.*?)\n```", text, re.S).group(1)
    payload = json.loads(json_block)
    v1_response = text.split("## LLM-generated report")[-1].strip()
    return payload, v1_response


EXAMPLES = [
    {"name": "commit6_rollback",
     "v1_path": os.path.join(ROOT, "chapter4", "tables", "4_7_1_llm_example_commit6_rollback.md"),
     "label": "Commit 6 (real ROLLBACK, GitHub demo)"},
    {"name": "batch09_pass",
     "v1_path": os.path.join(ROOT, "chapter4", "tables", "4_7_3_batch20", "example_09_PASS.md"),
     "label": "Batch example 9 (real PASS, held-out test set)"},
]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for ex in EXAMPLES:
        payload, v1_response = load_v1_payload_and_response(ex["v1_path"])
        prompt_v2, margin = render_prompt_v2(
            payload["decision"], payload["thresholds"]["tau1"], payload["thresholds"]["tau2"],
            payload["failure_probability"], payload["top_features"])
        print(f"--- calling hermes (v2 prompt) for {ex['name']} ---", flush=True)
        v2_response = call_hermes(prompt_v2)

        out_path = os.path.join(OUT_DIR, f"4_7_4_v2_comparison_{ex['name']}.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(f"# Prompt v1 vs v2 comparison -- {ex['label']}\n\n")
            f.write(f"_Same real payload, same model (`{MODEL}` via {PROVIDER}), only the "
                    f"prompt changed. Risk margin computed for v2: **{margin}**._\n\n")
            f.write("## v1 output (original master prompt, 3 sections)\n\n")
            f.write(v1_response + "\n\n")
            f.write("## v2 output (developer-facing prompt, 4 sections)\n\n")
            f.write(v2_response + "\n")
        print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
