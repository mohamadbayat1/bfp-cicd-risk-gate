"""Chapter 4, section 4-7-1: worked LLM analysis-layer examples.

Renders the report_payload contract from a REAL demo-app risk-gate result
(demo-app/ci_gate_runs/commitN/risk_gate_result.json -- genuine SHAP data from a
real GitHub Actions run) into the master prompt template (LLM_PROMPT.md), and calls
it through the Hermes CLI's one-shot mode (`hermes -z ... --cli`), which is already
configured on this machine with a working NVIDIA NIM key pointing at
nvidia/llama-3.3-nemotron-super-49b-v1.5 -- an NVIDIA-published distillation of
Meta's Llama 3.3, i.e. a Llama-family open-weight model. This is a STAND-IN used
only to produce representative example text for the thesis; the architecture
described in Chapter 3 is a locally-hosted Ollama deployment. The prompt contract
(system rules + input schema + output format) is identical either way -- only the
serving location differs.
"""
from __future__ import annotations
import json, os, subprocess, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNS_DIR = os.path.join(ROOT, "demo-app", "ci_gate_runs")
OUT_DIR = os.path.join(ROOT, "chapter4", "tables")

SYSTEM_PROMPT = """You are a CI/CD build-failure analyst. You are given a single build's pre-build risk
assessment produced by a calibrated machine-learning model: a three-state decision, a
calibrated probability that the build will FAIL, and the top contributing features with
their values and SHAP attributions.

Rules:
- Use ONLY the data provided in the user message. Do NOT invent metrics, logs, test
  names, stack traces, file names, or history that are not present in the input.
- SHAP sign convention: positive SHAP increases failure risk; negative decreases it.
- If the evidence is weak or ambiguous, say so plainly. Do not overstate certainty.
- Be concise and concrete. No filler."""

USER_TEMPLATE = """Build risk assessment:
- Decision: {decision}  (PASS < tau1={tau1} <= WARN < tau2={tau2} <= ROLLBACK)
- Calibrated failure probability: {probability}
- Top contributing features (feature = value, SHAP):
{feature_lines}

Produce a short report with exactly these three sections:

1. **Likely cause** (1-2 sentences): the most probable reason this build is at the given
   risk level, grounded only in the features above.
2. **Contributing factors** (bullet list): each top feature that meaningfully raises or
   lowers risk, stating its direction (raises/lowers) and why, referencing its SHAP sign.
3. **Remediation suggestions** (bullet list): concrete, actionable steps the team could
   take before/at deployment to reduce the risk (e.g. for WARN: add targeted tests, split
   the change; for ROLLBACK: stage behind a flag, hold the deploy). Tie each suggestion to
   a specific contributing factor.

Constraints: ground every statement in the provided features; if a section has no support
in the data, write "Insufficient signal in the provided data." Do not add a fourth section."""

EXAMPLES = [
    {"name": "commit6_rollback", "commit_dir": "commit6",
     "label": "Commit 6 (real ROLLBACK -- restore ValueError fix, flagged from real prior-build failure)"},
    {"name": "commit2_pass", "commit_dir": "commit2",
     "label": "Commit 2 (real PASS -- add factorial function with tests)"},
]

MODEL = "nvidia/llama-3.3-nemotron-super-49b-v1.5"
PROVIDER = "NVIDIA NIM"


def decode_categoricals(payload: dict) -> dict:
    """The saved model's top_features carry the LABEL-ENCODED integer for
    categorical columns (e.g. git_prev_commit_resolution_status=0), not the
    original string category. Handing raw integers to the LLM invites exactly
    the kind of fabricated interpretation the prompt is meant to prevent (caught
    in a first pass: the model guessed "lack of resolution" for code 0, which is
    actually "build_found"). Decode back to the real label using the saved
    preprocessor's cat_maps_ before rendering the prompt."""
    import joblib
    demo_app_dir = os.path.join(ROOT, "demo-app")
    if demo_app_dir not in sys.path:
        sys.path.insert(0, demo_app_dir)  # so unpickling the vendored bfp.preprocess.Preprocessor resolves
    pre = joblib.load(os.path.join(demo_app_dir, "models", "preprocessor.joblib"))
    inverse = {col: {v: k for k, v in m.items()} for col, m in pre.cat_maps_.items()}
    out = json.loads(json.dumps(payload))  # deep copy
    for f in out["top_features"]:
        col = f["feature"]
        if col in inverse:
            code = int(f["value"])
            f["value"] = inverse[col].get(code, f"unknown_category_{code}")
    return out


def render_prompt(payload: dict) -> str:
    feature_lines = "\n".join(
        f"  - {f['feature']} = {f['value']}  (SHAP {f['shap']:+.4f})"
        for f in payload["top_features"]
    )
    user = USER_TEMPLATE.format(
        decision=payload["decision"],
        tau1=payload["thresholds"]["tau1"],
        tau2=payload["thresholds"]["tau2"],
        probability=payload["failure_probability"],
        feature_lines=feature_lines,
    )
    return SYSTEM_PROMPT + "\n\n" + user


def call_hermes(prompt: str) -> str:
    result = subprocess.run(
        ["hermes", "-z", prompt, "--cli"],
        capture_output=True, text=True, encoding="utf-8", timeout=180,
    )
    if result.returncode != 0:
        raise RuntimeError(f"hermes call failed: {result.stderr}")
    return result.stdout.strip()


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    index_lines = ["# 4-7-1 — Worked LLM analysis-layer examples\n",
                   f"_Generated: {datetime.datetime.now().isoformat(timespec='seconds')}_\n",
                   f"_Model used for these examples: `{MODEL}` via {PROVIDER} (Hermes CLI, "
                   f"one-shot mode). This is an NVIDIA-published distillation of Meta's "
                   f"Llama 3.3 -- a Llama-family open-weight model -- used here as a "
                   f"stand-in to produce representative example text. The architecture "
                   f"described in Chapter 3 is a locally-hosted Ollama deployment; the "
                   f"prompt contract (system rules, input schema, three-section output "
                   f"format) is identical regardless of which model serves it._\n"]

    for ex in EXAMPLES:
        result_path = os.path.join(RUNS_DIR, ex["commit_dir"], "risk_gate_result.json")
        with open(result_path) as f:
            payload_raw = json.load(f)
        payload = decode_categoricals(payload_raw)

        prompt = render_prompt(payload)
        print(f"--- calling hermes for {ex['name']} ---", flush=True)
        response = call_hermes(prompt)

        out_path = os.path.join(OUT_DIR, f"4_7_1_llm_example_{ex['name']}.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(f"# LLM analysis-layer example — {ex['label']}\n\n")
            f.write(f"_Model: `{MODEL}` via {PROVIDER}, real data from "
                    f"`demo-app/ci_gate_runs/{ex['commit_dir']}/risk_gate_result.json`_\n\n")
            f.write("## Input (report_payload)\n\n```json\n")
            f.write(json.dumps(payload, indent=2))
            f.write("\n```\n\n## LLM-generated report\n\n")
            f.write(response)
            f.write("\n")
        print(f"wrote {out_path}")
        index_lines.append(f"- [{ex['label']}](4_7_1_llm_example_{ex['name']}.md)")

    with open(os.path.join(OUT_DIR, "4_7_1_llm_examples_index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(index_lines) + "\n")
    print("wrote index")


if __name__ == "__main__":
    main()
