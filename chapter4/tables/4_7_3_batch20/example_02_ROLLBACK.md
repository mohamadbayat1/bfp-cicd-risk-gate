# Batch example 2/20 -- decision ROLLBACK, actual fail (correct-catch)

_Model: `nvidia/llama-3.3-nemotron-super-49b-v1.5` via NVIDIA NIM. Real held-out test-set build, test-split row index 57889._

## Input (report_payload, categoricals decoded)

```json
{
  "decision": "ROLLBACK",
  "failure_probability": 0.5399187084806005,
  "thresholds": {
    "tau1": 0.11189963272616212,
    "tau2": 0.4661517258048494
  },
  "top_features": [
    {
      "feature": "hist_prev_status",
      "value": 1.0,
      "shap": 0.16793360342576308
    },
    {
      "feature": "hist_consec_fail",
      "value": 1.0,
      "shap": 0.14624035392711449
    },
    {
      "feature": "hist_fail_rate_20",
      "value": 0.550000011920929,
      "shap": 0.061457587697588176
    },
    {
      "feature": "hist_fail_rate_all",
      "value": 0.4736842215061188,
      "shap": 0.048872031393855264
    },
    {
      "feature": "hist_fail_rate_5",
      "value": 0.6000000238418579,
      "shap": 0.0399597887225924
    },
    {
      "feature": "git_prev_commit_resolution_status",
      "value": "build_found",
      "shap": 0.011732572808664816
    }
  ]
}
```

## Ground truth (NOT shown to the model or the LLM)

Actual outcome: **fail** -> correct-catch

## LLM-generated report

1. **Likely cause**:  
The build is at high risk of failure primarily due to historical patterns of instability: the previous status being a failure (`hist_prev_status=1.0`, +0.1679 SHAP) and consecutive prior failures (`hist_consec_fail=1.0`, +0.1462 SHAP) strongly indicate systemic issues. Elevated historical failure rates (`hist_fail_rate_20=0.55`, `hist_fail_rate_all=0.4737`, `hist_fail_rate_5=0.6`) further reinforce this trend.

2. **Contributing factors**:  
- `hist_prev_status=1.0`: **Raises** risk (+0.1679 SHAP) — indicates the previous build failed, creating uncertainty about current stability.  
- `hist_consec_fail=1.0`: **Raises** risk (+0.1462 SHAP) — consecutive failures suggest unresolved systemic problems.  
- `hist_fail_rate_20=0.55`: **Raises** risk (+0.0615 SHAP) — recent failure rate above 50% signals persistent issues.  
- `hist_fail_rate_all=0.4737`: **Raises** risk (+0.0489 SHAP) — long-term failure rate near 50% indicates chronic instability.  
- `hist_fail_rate_5=0.6`: **Raises** risk (+0.0400 SHAP) — very recent failure rate above 50% compounds near-term risk.  
- `git_prev_commit_resolution_status=build_found`: **Slightly raises** risk (+0.0117 SHAP) — previous commit had build-related issues, reducing confidence in this change.

3. **Remediation suggestions**:  
- **Stabilize prior failures**: Address root causes of previous build failures (linked to `hist_prev_status` and `hist_consec_fail`) through targeted debugging and regression tests.  
- **Improve test coverage**: Reduce `hist_fail_rate_5`/`hist_fail_rate_20` by strengthening validation for frequently failing components.  
- **Stage deployment behind a feature flag**: Mitigate impact of potential failure (aligned with ROLLBACK decision) by enabling gradual rollout and Monitoring.  
- **Analyze historical patterns**: Investigate systemic causes of `hist_fail_rate_all=0.4737` (e.g., flaky tests, infrastructure issues) to reduce long-term risk.  
- **Verify commit resolution**: Ensure `git_prev_commit_resolution_status` is resolved to "fixed" or "verified" before reattempting deploy.
