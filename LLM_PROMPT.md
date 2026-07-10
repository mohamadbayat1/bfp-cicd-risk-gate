# LLM Analysis-Layer Prompt (main version)

**This is the production prompt of the analysis layer** — the four-section,
developer-facing prompt described in thesis Chapters 3–4. It was refined through
testing against real model outputs on real builds (see "Design notes" at the end);
this file contains only the final version. Real generated examples live in
`chapter4/tables/4_7_*`.

**Model:** a Llama-family open-weight model, called through an API. The prompt contract
is model- and host-independent; the planned production setup is a **self-hosted
Llama-family model** (the API provider used during evaluation was only a serving
convenience and is not part of the design).

**Exact model used for every generated example (reproducibility):**
`nvidia/llama-3.3-nemotron-super-49b-v1.5` — a 49B-parameter Llama-3.3 derivative.
The thesis (Chapter 4 §۴-۷) names it as «Llama-3.3-Nemotron-Super-49B»; the API
provider is deliberately not named in thesis text.

**Invocation policy:** the layer is called **only for WARN and ROLLBACK** decisions —
a PASS build gets no LLM call at all (verified with a real three-state test:
`chapter4/tables/4_7_5_conditional_policy_test.md`). The layer is explanation-only;
it never changes the gate decision.

---

## Input contract (filled from `InferencePipeline.predict(...)`)

```json
{
  "build_id": "<string, optional context>",
  "decision": "PASS | WARN | ROLLBACK",
  "failure_probability": 0.0,
  "thresholds": { "tau1": 0.0, "tau2": 0.0 },
  "top_features": [
    { "feature": "<name>", "value": 0.0, "shap": 0.0 }
  ]
}
```

`shap > 0` pushes the build toward FAILURE; `shap < 0` pushes toward PASS. Features are
pre-build signals only (churn/diff sizes, test density, repo/team metadata, language,
PR flag, previous-commit resolution status, `churn_ratio`, `test_coverage_proxy`, and
the six `hist_*` history features).

**Critical preprocessing rule (learned from a real caught hallucination):**
`InferencePipeline._top_features()` returns the label-encoded **integer** for
categorical features. Feeding the raw integer to the LLM produced a real fabricated
interpretation in testing. **Always decode categoricals back to their string label**
(via the saved preprocessor's `cat_maps_`) before building the prompt.

---

## Code-computed inputs (never left to the model)

**1. Plain-English label for every feature:**

```python
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
```

**2. Qualitative risk margin** (how close p is to the decision boundary — the model
must calibrate its tone to this):

```python
def risk_margin(p, tau1, tau2, decision):
    if decision == "PASS":
        frac = (tau1 - p) / tau1 if tau1 > 0 else 1.0
        return "well below the WARN threshold" if frac > 0.5 else "just below the WARN threshold"
    if decision == "WARN":
        frac = (p - tau1) / (tau2 - tau1)
        return ("just above the WARN threshold" if frac < 0.33
                else "in the middle of the WARN range" if frac < 0.66
                else "close to the ROLLBACK threshold")
    frac = min(1.0, (p - tau2) / (1 - tau2))
    return ("just above the ROLLBACK threshold" if frac < 0.33
            else "well above the ROLLBACK threshold" if frac < 0.66
            else "very deep into ROLLBACK territory")
```

---

## System prompt

```
You are a CI/CD build-risk assistant writing a short note for a software developer who
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
- Be concise. No filler.
```

## User prompt template

```
Build risk assessment:
- Decision: {{decision}}
- Calibrated failure probability: {{failure_probability}}
- Risk margin: {{margin}}
- Contributing signals (plain description = raw value, SHAP):
{{#each top_features}}
  - {{plain_label}} [{{feature}}] = {{value}}  (SHAP {{shap}})
{{/each}}

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
write "Insufficient signal in the provided data." Do not add a fifth section.
```

---

## Design notes (why the prompt looks like this)

The prompt was hardened against real model outputs on real held-out builds, not just
designed on paper. Concretely:

- **Groundedness:** the "use ONLY the provided data" rule is enforceable only when the
  data itself is readable — a raw label-encoded categorical produced a real fabricated
  interpretation; the fix is the code-level decoding rule above.
- **Tone calibration:** without the risk-margin input, a barely-over-threshold ROLLBACK
  read as alarmist as an extreme one; the margin string fixes the tone.
- **Consistent terminology:** FEATURE_LABELS exists because the model translated raw
  feature names inconsistently when left to improvise.
- **Completeness:** the "mention every provided feature" rule exists because one report
  silently dropped a feature.

Real before/after evidence and worked examples: `chapter4/tables/4_7_4_v2_comparison_*.md`,
`chapter4/tables/4_7_1_*`, `chapter4/tables/4_7_3_batch20/`.
