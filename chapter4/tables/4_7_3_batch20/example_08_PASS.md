# Batch example 8/20 -- decision PASS, actual pass (correct-pass)

_Model: `nvidia/llama-3.3-nemotron-super-49b-v1.5` via NVIDIA NIM. Real held-out test-set build, test-split row index 38324._

## Input (report_payload, categoricals decoded)

```json
{
  "decision": "PASS",
  "failure_probability": 0.061998869736003666,
  "thresholds": {
    "tau1": 0.11189963272616212,
    "tau2": 0.4661517258048494
  },
  "top_features": [
    {
      "feature": "hist_fail_rate_all",
      "value": 0.3513513505458832,
      "shap": 0.047132576283816084
    },
    {
      "feature": "hist_fail_rate_5",
      "value": 0.0,
      "shap": -0.022041255363287462
    },
    {
      "feature": "hist_fail_rate_20",
      "value": 0.15000000596046448,
      "shap": 0.02073779642405647
    },
    {
      "feature": "hist_consec_fail",
      "value": 0.0,
      "shap": -0.016609743968984958
    },
    {
      "feature": "gh_diff_other_files",
      "value": 1.0,
      "shap": -0.014998531418312843
    },
    {
      "feature": "hist_prev_status",
      "value": 0.0,
      "shap": -0.013007380416308934
    }
  ]
}
```

## Ground truth (NOT shown to the model or the LLM)

Actual outcome: **pass** -> correct-pass

## LLM-generated report

**Likely cause**  
The build is at low risk (PASS, 6.2% failure probability) primarily due to moderate historical instability (all-time failure rate of 35.1% and 20-build failure rate of 15%) which increases risk. However, this is offset by recent stability (zero failures in the last 5 builds and no consecutive failures), which lowers risk.

**Contributing factors**  
- `hist_fail_rate_all = 0.3514` (SHAP +0.0471): Raises risk — higher all-time failure rate indicates historical instability.  
- `hist_fail_rate_5 = 0.0` (SHAP -0.0220): Lowers risk — no recent failures suggest improved stability.  
- `hist_fail_rate_20 = 0.1500` (SHAP +0.0207): Raises risk — 15% failure rate over 20 builds still contributes to caution.  
- `hist_consec_fail = 0.0` (SHAP -0.0166): Lowers risk — no consecutive failures imply isolated past issues.  
- `gh_diff_other_files = 1.0` (SHAP -0.0150): Lowers risk — changes in other files may indicate smaller, less disruptive modifications.  
- `hist_prev_status = 0.0` (SHAP -0.0130): Lowers risk — previous passing status reduces concern.

**Remediation suggestions**  
- **Reduce historical instability**: Audit and address root causes of past failures (e.g., flaky tests, infrastructure issues) to lower `hist_fail_rate_all` and `hist_fail_rate_20`.  
- **Maintain recent stability**: Enforce rigorous testing for new builds to preserve `hist_fail_rate_5 = 0`, preventing reversion to past instability.  
- **Leverage contained changes**: Where possible, scope changes to affect fewer files (aligned with `gh_diff_other_files = 1.0` lowering risk) to minimize blast radius.  
- **Monitor consecutive failures**: Implement alerts for repeated failures to keep `hist_consec_fail = 0` and prevent cascading issues.
