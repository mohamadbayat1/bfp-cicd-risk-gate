# LLM analysis-layer example — Commit 2 (real PASS -- add factorial function with tests)

_Model: `nvidia/llama-3.3-nemotron-super-49b-v1.5` via NVIDIA NIM, real data from `demo-app/ci_gate_runs/commit2/risk_gate_result.json`_

## Input (report_payload)

```json
{
  "failure_probability": 0.07429670076982905,
  "rf_probability": 0.21851041820067643,
  "decision": "PASS",
  "thresholds": {
    "tau1": 0.11189963272616212,
    "tau2": 0.4661517258048494
  },
  "top_features": [
    {
      "feature": "hist_build_seq",
      "value": 0.0,
      "shap": 0.10666188752478503
    },
    {
      "feature": "hist_fail_rate_20",
      "value": 0.0,
      "shap": -0.04539762395102221
    },
    {
      "feature": "hist_fail_rate_all",
      "value": 0.0,
      "shap": -0.03722324458702052
    },
    {
      "feature": "hist_consec_fail",
      "value": 0.0,
      "shap": -0.01610817222997184
    },
    {
      "feature": "git_prev_commit_resolution_status",
      "value": "no_previous_build",
      "shap": -0.016045393314981508
    },
    {
      "feature": "hist_prev_status",
      "value": 0.0,
      "shap": -0.012492181782045008
    }
  ]
}
```

## LLM-generated report

1. **Likely cause**:  
The build shows increased failure risk primarily due to **hist_build_seq = 0.0** (no recent build history), which contributes +0.1067 SHAP (positive risk). This suggests uncertainty from lack of prior execution context. Other features (low historical failure rates, no consecutive failures) reduce risk but are outweighed by the absence of build sequence data.

2. **Contributing factors**:  
- **hist_build_seq = 0.0** raises risk: Positive SHAP indicates no prior builds increase uncertainty.  
- **hist_fail_rate_20 = 0.0** lowers risk: Negative SHAP suggests zero failures in the last 20 builds reduce risk.  
- **hist_fail_rate_all = 0.0** lowers risk: Negative SHAP indicates historically low failure rate decreases risk.  
- **hist_consec_fail = 0.0** lowers risk: Negative SHAP shows no consecutive failures reduce risk.  
- **git_prev_commit_resolution_status = no_previous_build** lowers risk: Negative SHAP implies starting fresh avoids inherited issues.  
- **hist_prev_status = 0.0** lowers risk: Negative SHAP suggests prior success state reduces risk.  

3. **Remediation suggestions**:  
- **For hist_build_seq**: Run pre-build verification steps (e.g., dry-run deployments, smoke tests) to establish confidence in the build process.  
- **For low historical failure rates**: Maintain monitoring to ensure historical success trends continue (e.g., alert on new failure patterns).  
- **For no previous build**: Stage the deployment behind a feature flag or canary release to validate in production before full rollout.  

No additional actions are warranted for negative-contributing features already at optimal values (0.0).
