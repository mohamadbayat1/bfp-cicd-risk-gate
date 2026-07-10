"""Chapter 4, section 4-7 extension: batch LLM evaluation on 20 REAL held-out test builds.

Unlike the 2 earlier worked examples (from the tiny GitHub demo repo), these 20 come
from the actual 138,669-build held-out TEST split of the real historical dataset --
the same split used for the headline ROC-AUC/PR-AUC/Brier numbers. Stratified 7/7/6
across PASS/WARN/ROLLBACK (using the already-rescored, sanity-checked probabilities in
chapter4/data/rescored_test.npz) so all three decision states are represented. For
each: real raw features -> real InferencePipeline (model+calibrator+SHAP, unchanged
from training) -> real decision -> master prompt -> Hermes CLI (same model as the
earlier 2 examples) -> LLM report. Also reports whether the decision matched the
build's REAL actual outcome (ground truth), which the model/LLM never see.
"""
from __future__ import annotations
import json, os, sys, subprocess, datetime
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from bfp import config as C, data, splits  # noqa: E402
from bfp.inference import InferencePipeline  # noqa: E402

OUT_DIR = os.path.join(ROOT, "chapter4", "tables")
DETAIL_DIR = os.path.join(ROOT, "chapter4", "tables", "4_7_3_batch20")
SEED = 123  # separate from the training seed -- this is a fresh illustrative sample
N_PER_BUCKET = {"PASS": 7, "WARN": 7, "ROLLBACK": 6}

MODEL = "nvidia/llama-3.3-nemotron-super-49b-v1.5"
PROVIDER = "NVIDIA NIM"

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


def render_prompt(decision, tau1, tau2, probability, top_features):
    feature_lines = "\n".join(
        f"  - {f['feature']} = {f['value']}  (SHAP {f['shap']:+.4f})" for f in top_features
    )
    user = USER_TEMPLATE.format(decision=decision, tau1=tau1, tau2=tau2,
                                 probability=probability, feature_lines=feature_lines)
    return SYSTEM_PROMPT + "\n\n" + user


def call_hermes(prompt: str) -> str:
    # encoding="utf-8" explicitly -- without it, Windows' default locale encoding
    # mangles em-dashes/curly quotes in the model's output (mojibake)
    result = subprocess.run(["hermes", "-z", prompt, "--cli"],
                             capture_output=True, text=True, encoding="utf-8", timeout=180)
    if result.returncode != 0:
        raise RuntimeError(f"hermes call failed: {result.stderr}")
    return result.stdout.strip()


def decode_categoricals(top_features, cat_maps):
    inverse = {col: {v: k for k, v in m.items()} for col, m in cat_maps.items()}
    out = []
    for f in top_features:
        f = dict(f)
        if f["feature"] in inverse:
            f["value"] = inverse[f["feature"]].get(int(f["value"]), f"unknown_category_{int(f['value'])}")
        out.append(f)
    return out


def log(msg):
    print(f"[{datetime.datetime.now().isoformat(timespec='seconds')}] {msg}", flush=True)


def main():
    os.makedirs(DETAIL_DIR, exist_ok=True)

    log("loading full dataset + reproducing the exact grouped split (seed=42)")
    df = data.load_builds()
    sp = splits.make_splits(df)
    test_df = sp["test"].reset_index(drop=True)

    rescored = np.load(os.path.join(ROOT, "chapter4", "data", "rescored_test.npz"))
    y_all, p_all = rescored["y"], rescored["p"]
    assert len(y_all) == len(test_df), "rescored_test.npz and the reproduced test split must align"
    tau1, tau2 = 0.11189963272616212, 0.4661517258048494
    dec_all = np.where(p_all < tau1, "PASS", np.where(p_all < tau2, "WARN", "ROLLBACK"))

    rng = np.random.RandomState(SEED)
    chosen_idx = []
    for bucket, n in N_PER_BUCKET.items():
        pool = np.where(dec_all == bucket)[0]
        chosen_idx.extend(rng.choice(pool, size=n, replace=False))
    rng.shuffle(chosen_idx)
    log(f"selected {len(chosen_idx)} builds: {dict(zip(*np.unique(dec_all[chosen_idx], return_counts=True)))}")

    log("loading InferencePipeline (real saved model, calibrator, SHAP explainer)")
    pipe = InferencePipeline(models_dir=C.MODELS_DIR, with_shap=True)
    cat_maps = pipe.pre.cat_maps_

    sample_df = test_df.iloc[chosen_idx].reset_index(drop=True)
    results = pipe.predict(sample_df, top_k=6)

    rows_summary = []
    for i, (idx, r) in enumerate(zip(chosen_idx, results)):
        actual_y = int(y_all[idx])
        actual_label = "fail" if actual_y == 1 else "pass"
        correctness = (
            "correct-catch" if (r["decision"] in ("WARN", "ROLLBACK") and actual_y == 1) else
            "false-alarm" if (r["decision"] in ("WARN", "ROLLBACK") and actual_y == 0) else
            "missed-failure" if (r["decision"] == "PASS" and actual_y == 1) else
            "correct-pass"
        )
        top_features_decoded = decode_categoricals(r["top_features"], cat_maps)
        prompt = render_prompt(r["decision"], r["thresholds"]["tau1"], r["thresholds"]["tau2"],
                                r["failure_probability"], top_features_decoded)
        log(f"[{i+1}/20] idx={idx} decision={r['decision']} p={r['failure_probability']:.4f} "
            f"actual={actual_label} ({correctness}) -- calling hermes")
        response = call_hermes(prompt)

        detail_path = os.path.join(DETAIL_DIR, f"example_{i+1:02d}_{r['decision']}.md")
        with open(detail_path, "w", encoding="utf-8") as f:
            f.write(f"# Batch example {i+1}/20 -- decision {r['decision']}, actual {actual_label} ({correctness})\n\n")
            f.write(f"_Model: `{MODEL}` via {PROVIDER}. Real held-out test-set build, "
                    f"test-split row index {idx}._\n\n")
            f.write("## Input (report_payload, categoricals decoded)\n\n```json\n")
            f.write(json.dumps({
                "decision": r["decision"], "failure_probability": r["failure_probability"],
                "thresholds": r["thresholds"], "top_features": top_features_decoded,
            }, indent=2))
            f.write("\n```\n\n## Ground truth (NOT shown to the model or the LLM)\n\n")
            f.write(f"Actual outcome: **{actual_label}** -> {correctness}\n\n")
            f.write("## LLM-generated report\n\n")
            f.write(response + "\n")

        rows_summary.append({
            "n": i + 1, "idx": int(idx), "decision": r["decision"],
            "probability": r["failure_probability"], "actual": actual_label,
            "correctness": correctness, "top_feature": top_features_decoded[0]["feature"],
        })

    index_lines = ["# 4-7-3 — Batch LLM evaluation on 20 real held-out test builds\n",
                   f"_Generated: {datetime.datetime.now().isoformat(timespec='seconds')}_\n",
                   f"_Model: `{MODEL}` via {PROVIDER} (Hermes CLI, one-shot). Stratified sample "
                   f"({N_PER_BUCKET}) from the real 138,669-build test split, seed={SEED}. "
                   f"Ground truth (actual pass/fail) was NOT given to the model or the LLM -- "
                   f"shown here only to assess correctness after the fact._\n",
                   "| # | Decision | p(fail) | Actual | Match | Top feature |",
                   "|---|---|---|---|---|---|"]
    for row in rows_summary:
        index_lines.append(f"| {row['n']} | {row['decision']} | {row['probability']:.4f} | "
                            f"{row['actual']} | {row['correctness']} | {row['top_feature']} |")

    counts = {}
    for row in rows_summary:
        counts[row["correctness"]] = counts.get(row["correctness"], 0) + 1
    index_lines.append("")
    index_lines.append(f"_Correctness breakdown over these 20: {counts}_")
    index_lines.append("")
    index_lines.append(f"Full input+LLM output for each example: `4_7_3_batch20/example_NN_DECISION.md`")

    with open(os.path.join(OUT_DIR, "4_7_3_batch20_summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(index_lines) + "\n")
    log("wrote 4_7_3_batch20_summary.md")


if __name__ == "__main__":
    main()
