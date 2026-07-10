# Batch example 12/20 -- decision WARN, actual pass (false-alarm)

_Model: `nvidia/llama-3.3-nemotron-super-49b-v1.5` via NVIDIA NIM. Real held-out test-set build, test-split row index 132791._

## Input (report_payload, categoricals decoded)

```json
{
  "decision": "WARN",
  "failure_probability": 0.18919899714600447,
  "thresholds": {
    "tau1": 0.11189963272616212,
    "tau2": 0.4661517258048494
  },
  "top_features": [
    {
      "feature": "hist_fail_rate_20",
      "value": 0.30000001192092896,
      "shap": 0.05868212987943704
    },
    {
      "feature": "hist_fail_rate_all",
      "value": 0.323922723531723,
      "shap": 0.053051411473989986
    },
    {
      "feature": "hist_fail_rate_5",
      "value": 0.4000000059604645,
      "shap": 0.04551302367946164
    },
    {
      "feature": "git_num_all_built_commits",
      "value": 2.0,
      "shap": 0.03760041060582207
    },
    {
      "feature": "hist_consec_fail",
      "value": 0.0,
      "shap": -0.012685725532030574
    },
    {
      "feature": "hist_prev_status",
      "value": 0.0,
      "shap": -0.009057910636311135
    }
  ]
}
```

## Ground truth (NOT shown to the model or the LLM)

Actual outcome: **pass** -> false-alarm

## LLM-generated report

**Likely cause**  
The build is flagged as WARN primarily due to elevated historical failure rates: the project has a 30% failure rate in the last 20 builds, 32.4% overall, and 40% in the last 5 builds. These metrics indicate a pattern of instability that the model associates with increased failure risk.  

**Contributing factors**  
- `hist_fail_rate_20 = 0.3` (SHAP +0.0587): Raises risk — frequent recent failures suggest unresolved issues in the build process.  
- `hist_fail_rate_all = 0.324` (SHAP +0.0531): Raises risk — long-term instability patterns correlate with higher failure likelihood.  
- `hist_fail_rate_5 = 0.4` (SHAP +0.0455): Raises risk — very high short-term failure rate, indicating acute instability.  
- `git_num_all_built_commits = 2.0` (SHAP +0.0376): Raises risk — small commit count may signal insufficient testing or incomplete changes.  
- `hist_consec_fail = 0.0` (SHAP -0.0127): Lowers risk — no recent consecutive failures, reducing immediate concern.  
- `hist_prev_status = 0.0` (SHAP -0.0091): Lowers risk — previous build succeeded, slightly offsetting other risks.  

**Remediation suggestions**  
- **Targeted testing**: Focus on areas that caused failures in the last 5 builds (linked to `hist_fail_rate_5`).  
- **Split changes**: Reduce `git_num_all_built_commits` impact by breaking changes into smaller, incremental commits for better isolation and validation.  
- **Root cause analysis**: Investigate historical failures (linked to `hist_fail_rate_all` and `hist_fail_rate_20`) to address systemic issues in the build pipeline.  
- **Monitor stability**: Ensure no consecutive failures occur (to maintain `hist_consec_fail = 0`) by implementing automated rollback or alerting for early failure detection.
