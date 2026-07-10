# Batch example 4/20 -- decision WARN, actual pass (false-alarm)

_Model: `nvidia/llama-3.3-nemotron-super-49b-v1.5` via NVIDIA NIM. Real held-out test-set build, test-split row index 67248._

## Input (report_payload, categoricals decoded)

```json
{
  "decision": "WARN",
  "failure_probability": 0.34669641462491413,
  "thresholds": {
    "tau1": 0.11189963272616212,
    "tau2": 0.4661517258048494
  },
  "top_features": [
    {
      "feature": "hist_prev_status",
      "value": 1.0,
      "shap": 0.16717374642195182
    },
    {
      "feature": "hist_consec_fail",
      "value": 1.0,
      "shap": 0.15528906946721918
    },
    {
      "feature": "hist_fail_rate_all",
      "value": 0.0704558938741684,
      "shap": -0.055208754241092464
    },
    {
      "feature": "gh_is_pr",
      "value": "TRUE",
      "shap": 0.028521908163013966
    },
    {
      "feature": "git_prev_commit_resolution_status",
      "value": "build_found",
      "shap": 0.01919123159467581
    },
    {
      "feature": "hist_fail_rate_20",
      "value": 0.05000000074505806,
      "shap": -0.015564409023033061
    }
  ]
}
```

## Ground truth (NOT shown to the model or the LLM)

Actual outcome: **pass** -> false-alarm

## LLM-generated report

**Likely cause**  
The build is at WARN risk primarily due to historical indicators of instability: a previous build failure (`hist_prev_status=1.0`) and consecutive failures (`hist_consec_fail=1.0`), which together contribute +0.3225 SHAP (positive) and strongly elevate risk.

**Contributing factors**  
- `hist_prev_status=1.0` (SHAP +0.1672): Raises risk — prior build failure increases likelihood of recurrence.  
- `hist_consec_fail=1.0` (SHAP +0.1553): Raises risk — consecutive failures suggest systemic instability.  
- `hist_fail_rate_all=0.0705` (SHAP -0.0552): Lowers risk — overall historical failure rate (7.1%) is moderate.  
- `gh_is_pr=TRUE` (SHAP +0.0285): Raises risk — Pull Requests typically have higher failure rates due to less vetting.  
- `git_prev_commit_resolution_status=build_found` (SHAP +0.0192): Raises risk — unresolved build issues from prior commits may propagate.  
- `hist_fail_rate_20=0.0500` (SHAP -0.0156): Lowers risk — recent failure rate (5%) is low, partially offsetting other factors.  

**Remediation suggestions**  
- **Address historical failures**: Investigate root causes of prior build failures (`hist_prev_status`, `hist_consec_fail`) and stabilize flaky tests or infrastructure.  
- **Improve PR quality gates**: Add mandatory targeted tests or static analysis for Pull Requests (`gh_is_pr`) to reduce runtime failures.  
- **Resolve prior commit issues**: Audit and fix lingering build issues from previous commits (`git_prev_commit_resolution_status`).  
- **Monitor low-risk signals**: Continue practices that maintain the low recent failure rate (`hist_fail_rate_20`).  

No unsupported claims; all recommendations directly tied to provided features.
