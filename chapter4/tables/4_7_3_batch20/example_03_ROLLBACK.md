# Batch example 3/20 -- decision ROLLBACK, actual fail (correct-catch)

_Model: `nvidia/llama-3.3-nemotron-super-49b-v1.5` via NVIDIA NIM. Real held-out test-set build, test-split row index 121728._

## Input (report_payload, categoricals decoded)

```json
{
  "decision": "ROLLBACK",
  "failure_probability": 0.7806907993897831,
  "thresholds": {
    "tau1": 0.11189963272616212,
    "tau2": 0.4661517258048494
  },
  "top_features": [
    {
      "feature": "hist_consec_fail",
      "value": 9.0,
      "shap": 0.27401957120590054
    },
    {
      "feature": "hist_prev_status",
      "value": 1.0,
      "shap": 0.21180789734604333
    },
    {
      "feature": "hist_fail_rate_5",
      "value": 1.0,
      "shap": 0.10793206319962813
    },
    {
      "feature": "hist_fail_rate_20",
      "value": 0.44999998807907104,
      "shap": 0.04713192432145176
    },
    {
      "feature": "hist_fail_rate_all",
      "value": 0.17768594622612,
      "shap": -0.006661217240785966
    },
    {
      "feature": "gh_diff_other_files",
      "value": 1.0,
      "shap": -0.006561936769845928
    }
  ]
}
```

## Ground truth (NOT shown to the model or the LLM)

Actual outcome: **fail** -> correct-catch

## LLM-generated report

**Likely cause**  
The build is at ROLLBACK risk primarily due to **9.0 consecutive prior failures (hist_consec_fail, +0.2740 SHAP)**, indicating a persistent instability in the build pipeline. This is compounded by **historical failure patterns (hist_prev_status=1.0, +0.2118 SHAP)** and **recent high failure rates in the last 5 builds (hist_fail_rate_5=1.0, +0.1079 SHAP)**.  

**Contributing factors**  
- `hist_consec_fail=9.0` **raises risk** (strong positive SHAP): 9 consecutive failures suggest systemic issues (e.g., flaky tests, infrastructure problems).  
- `hist_prev_status=1.0` **raises risk** (positive SHAP): The previous build failed, increasing confidence in the current failure prediction.  
- `hist_fail_rate_5=1.0` **raises risk** (positive SHAP): 100% failure rate in the last 5 builds reinforces the model’s high-risk assessment.  
- `hist_fail_rate_20=0.45` **moderately raises risk** (small positive SHAP): Elevated failure rate over 20 builds suggests unresolved instability.  
- `hist_fail_rate_all=0.178` **lowers risk slightly** (small negative SHAP): Lower overall failure rate may dampen risk but is outweighed by recent trends.  
- `gh_diff_other_files=1.0` **lowers risk minimally** (small negative SHAP): Changes in unrelated files may reduce risk, but impact is negligible here.  

**Remediation suggestions**  
- **Stage the deploy behind a feature flag** to allow rollback if issues arise (addresses `hist_consec_fail` and `hist_prev_status`).  
- **Investigate root causes of consecutive failures**: Audit logs for recurring errors in the last 9 builds and fix underlying issues (directly targets `hist_consec_fail`).  
- **Split the change into smaller, testable increments**: Reduce complexity to isolate failures (mitigates `hist_fail_rate_5` signal).  
- **Strengthen test coverage for high-risk areas**: Add targeted tests for components failing in recent builds (addresses `hist_fail_rate_5` and `hist_prev_status`).  
- **Analyze long-term failure trends (hist_fail_rate_20)**: Identify systemic issues contributing to elevated 20-build failure rates.
