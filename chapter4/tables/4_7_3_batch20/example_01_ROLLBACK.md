# Batch example 1/20 -- decision ROLLBACK, actual pass (false-alarm)

_Model: `nvidia/llama-3.3-nemotron-super-49b-v1.5` via NVIDIA NIM. Real held-out test-set build, test-split row index 3433._

## Input (report_payload, categoricals decoded)

```json
{
  "decision": "ROLLBACK",
  "failure_probability": 0.56718606389932,
  "thresholds": {
    "tau1": 0.11189963272616212,
    "tau2": 0.4661517258048494
  },
  "top_features": [
    {
      "feature": "hist_prev_status",
      "value": 1.0,
      "shap": 0.14919678961110322
    },
    {
      "feature": "hist_consec_fail",
      "value": 1.0,
      "shap": 0.13052652919347907
    },
    {
      "feature": "hist_fail_rate_20",
      "value": 0.6000000238418579,
      "shap": 0.11750777631342169
    },
    {
      "feature": "hist_fail_rate_5",
      "value": 0.6000000238418579,
      "shap": 0.0721857170647634
    },
    {
      "feature": "git_prev_commit_resolution_status",
      "value": "merge_found",
      "shap": -0.030101080504319668
    },
    {
      "feature": "hist_fail_rate_all",
      "value": 0.28977271914482117,
      "shap": 0.024294220627950062
    }
  ]
}
```

## Ground truth (NOT shown to the model or the LLM)

Actual outcome: **pass** -> false-alarm

## LLM-generated report

1. **Likely cause**:  
The build is flagged for rollback primarily due to repeated historical failures: the previous build failed (`hist_prev_status=1.0`, +0.1492 SHAP), and there was at least one consecutive prior failure (`hist_consec_fail=1.0`, +0.1305 SHAP). High recent failure rates (`hist_fail_rate_20=0.6`, +0.1175 SHAP; `hist_fail_rate_5=0.6`, +0.0722 SHAP) further elevate risk, indicating systemic instability in the codebase or deployment pipeline.

2. **Contributing factors**:  
- `hist_prev_status=1.0` (raises risk): Previous build failure strongly correlates with current failure risk (+0.1492 SHAP).  
- `hist_consec_fail=1.0` (raises risk): Consecutive failures historically increase current risk (+0.1305 SHAP).  
- `hist_fail_rate_20=0.6` (raises risk): 60% failure rate over the last 20 builds suggests systemic issues (+0.1175 SHAP).  
- `hist_fail_rate_5=0.6` (raises risk): Recent 5-build failure rate of 60% reinforces instability (+0.0722 SHAP).  
- `git_prev_commit_resolution_status=merge_found` (lowers risk slightly): Merge commits historically correlate with lower risk (-0.0301 SHAP), possibly due to code review rigor.  
- `hist_fail_rate_all=0.289` (raises risk slightly): Lifetime failure rate of ~29% adds moderate risk (+0.0243 SHAP).  

3. **Remediation suggestions**:  
- **Address prior failures**: Investigate and resolve root causes of the previous build failure (`hist_prev_status`) and consecutive failures (`hist_consec_fail`) to break the failure chain.  
- **Reduce recent failure rates**: Stabilize the pipeline by fixing flaky tests or refactoring high-risk components contributing to `hist_fail_rate_5` and `hist_fail_rate_20`.  
- **Monitor merge commits**: While merges slightly reduce risk (`git_prev_commit_resolution_status`), ensure merge processes remain rigorous to maintain this trend.  
- **Mitigate lifetime failure rate**: Conduct a broader audit of historical failures (`hist_fail_rate_all`) to address recurring issues.
