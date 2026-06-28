# LLM Analysis-Layer Prompt Template

This is the prompt for the (not-yet-implemented) LLM analysis layer described in
Chapter 3. It is **not called anywhere in the pipeline.** The offline/inference code
produces the structured `report_payload` below (decision, calibrated failure
probability, top SHAP features with values); this template turns that payload into a
short human-readable analysis.

> **TODO (decide later):** choose the LLM model and API for this layer. Default to the
> latest, most capable Claude model (e.g. `claude-opus-4-8`) via the Anthropic API.
> Pin the model id, temperature (suggest 0.2 for determinism), and max tokens here once
> chosen. Until then this file is a specification only.

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

`shap > 0` pushes the build toward FAILURE; `shap < 0` pushes toward PASS. The features
are pre-build signals only (code churn, diff sizes, test density, repo/team metadata,
language, PR flag, previous-commit resolution status, and the engineered `churn_ratio`
and `test_coverage_proxy`).

---

## System prompt

```
You are a CI/CD build-failure analyst. You are given a single build's pre-build risk
assessment produced by a calibrated machine-learning model: a three-state decision, a
calibrated probability that the build will FAIL, and the top contributing features with
their values and SHAP attributions.

Rules:
- Use ONLY the data provided in the user message. Do NOT invent metrics, logs, test
  names, stack traces, file names, or history that are not present in the input.
- SHAP sign convention: positive SHAP increases failure risk; negative decreases it.
- If the evidence is weak or ambiguous, say so plainly. Do not overstate certainty.
- Be concise and concrete. No filler.
```

## User prompt (template — substitute the JSON payload)

```
Build risk assessment:
- Decision: {{decision}}  (PASS < tau1={{thresholds.tau1}} <= WARN < tau2={{thresholds.tau2}} <= ROLLBACK)
- Calibrated failure probability: {{failure_probability}}
- Top contributing features (feature = value, SHAP):
{{#each top_features}}
  - {{feature}} = {{value}}  (SHAP {{shap}})
{{/each}}

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
in the data, write "Insufficient signal in the provided data." Do not add a fourth section.
```

---

## Notes for thesis write-up
- The layer is explanation-only; it never changes the decision (the decision comes from
  the calibrated probability and the validation-selected thresholds tau1/tau2).
- Keeping the LLM constrained to the per-build payload prevents hallucinated root causes
  and keeps the analysis reproducible and auditable.
