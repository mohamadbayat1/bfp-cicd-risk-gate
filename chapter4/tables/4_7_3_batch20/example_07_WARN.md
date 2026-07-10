# Batch example 7/20 -- decision WARN, actual pass (false-alarm)

_Model: `nvidia/llama-3.3-nemotron-super-49b-v1.5` via NVIDIA NIM. Real held-out test-set build, test-split row index 79904._

## Input (report_payload, categoricals decoded)

```json
{
  "decision": "WARN",
  "failure_probability": 0.46505953387119814,
  "thresholds": {
    "tau1": 0.11189963272616212,
    "tau2": 0.4661517258048494
  },
  "top_features": [
    {
      "feature": "hist_prev_status",
      "value": 1.0,
      "shap": 0.1494888660675224
    },
    {
      "feature": "hist_consec_fail",
      "value": 1.0,
      "shap": 0.13607031460880648
    },
    {
      "feature": "hist_fail_rate_5",
      "value": 0.4000000059604645,
      "shap": 0.02363390062422475
    },
    {
      "feature": "git_prev_commit_resolution_status",
      "value": "build_found",
      "shap": 0.0231312348317131
    },
    {
      "feature": "hist_fail_rate_20",
      "value": 0.25,
      "shap": 0.019122394710553863
    },
    {
      "feature": "gh_diff_other_files",
      "value": 5.0,
      "shap": 0.016543645379886698
    }
  ]
}
```

## Ground truth (NOT shown to the model or the LLM)

Actual outcome: **pass** -> false-alarm

## LLM-generated report

1. **Likely cause**:  
The build is at WARN risk primarily due to historical instability indicators: the previous build status being non-passing (`hist_prev_status=1.0`, +0.1495 SHAP) and consecutive prior failures (`hist_consec_fail=1.0`, +0.1361 SHAP). These signal persistent issues in the codebase or deployment pipeline that increase failure likelihood.

2. **Contributing factors**:  
- `hist_prev_status=1.0`: **Raises** risk (positive SHAP +0.1495) — indicates unresolved issues from the previous build.  
- `hist_consec_fail=1.0`: **Raises** risk (positive SHAP +0.1361) — consecutive failures suggest systemic instability.  
- `hist_fail_rate_5=0.4`: **Raises** risk (positive SHAP +0.0236) — 40% failure rate in the last 5 builds shows recent unreliability.  
- `hist_fail_rate_20=0.25`: **Raises** risk (positive SHAP +0.0191) — 25% failure rate over 20 builds indicates long-term issues.  
- `git_diff_other_files=5.0`: **Raises** risk (positive SHAP +0.0165) — changes to 5+ files increase deployment complexity and uncertainty.  
- `git_prev_commit_resolution_status=build_found`: **Raises** risk (positive SHAP +0.0231) — prior commit resolved a build issue, but lingering side effects may persist.

3. **Remediation suggestions**:  
- **Stabilize prior builds**: Address root causes of previous failures (`hist_prev_status`, `hist_consec_fail`) by triaging historical issues and ensuring recent fixes are robust.  
- **Reduce concurrent changes**: Split the current PR into smaller, focused changes to minimize `git_diff_other_files` impact.  
- **Monitor failure trends**: Investigate and address the underlying causes of high `hist_fail_rate_5` and `hist_fail_rate_20` (e.g., flaky tests, environment issues).  
- **Validate commit resolution**: Double-check fixes from the prior commit (`git_prev_commit_resolution_status`) to ensure no residual issues exist.  
- **Implement incremental deployment**: Use feature flags or canary releases to mitigate risk from `git_diff_other_files` and historical instability.
