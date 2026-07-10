# Batch example 10/20 -- decision ROLLBACK, actual fail (correct-catch)

_Model: `nvidia/llama-3.3-nemotron-super-49b-v1.5` via NVIDIA NIM. Real held-out test-set build, test-split row index 118503._

## Input (report_payload, categoricals decoded)

```json
{
  "decision": "ROLLBACK",
  "failure_probability": 0.8507777563048903,
  "thresholds": {
    "tau1": 0.11189963272616212,
    "tau2": 0.4661517258048494
  },
  "top_features": [
    {
      "feature": "hist_consec_fail",
      "value": 7.0,
      "shap": 0.26161023967495795
    },
    {
      "feature": "hist_prev_status",
      "value": 1.0,
      "shap": 0.207373042992906
    },
    {
      "feature": "hist_fail_rate_5",
      "value": 1.0,
      "shap": 0.1075681201018098
    },
    {
      "feature": "hist_fail_rate_20",
      "value": 0.8500000238418579,
      "shap": 0.07676412989427543
    },
    {
      "feature": "hist_fail_rate_all",
      "value": 0.7740384340286255,
      "shap": 0.057972350187594446
    },
    {
      "feature": "git_num_all_built_commits",
      "value": 2.0,
      "shap": 0.016068004654501103
    }
  ]
}
```

## Ground truth (NOT shown to the model or the LLM)

Actual outcome: **fail** -> correct-catch

## LLM-generated report

**Likely cause**  
The build is at high risk primarily due to historical failure patterns: 7 consecutive prior failures (hist_consec_fail=7.0, SHAP +0.2616) and a history of previous build failures (hist_prev_status=1.0, SHAP +0.2074). These factors dominate the model's prediction, indicating unresolved instability in the build pipeline.

**Contributing factors**  
- **hist_consec_fail=7.0 (SHAP +0.2616)**: Raises risk — 7 consecutive failures strongly signal systemic issues (e.g., flaky tests, environment drift).  
- **hist_prev_status=1.0 (SHAP +0.2074)**: Raises risk — prior builds failing increases confidence in the model's failure prediction.  
- **hist_fail_rate_5=1.0 (SHAP +0.1076)**: Raises risk — 100% failure rate in the last 5 builds amplifies urgency.  
- **hist_fail_rate_20=0.85 (SHAP +0.0768)**: Raises risk — 85% failure rate in the last 20 builds suggests persistent problems.  
- **hist_fail_rate_all=0.774 (SHAP +0.0580)**: Raises risk — historical failure rate of 77.4% reinforces long-term instability.  
- **git_num_all_built_commits=2.0 (SHAP +0.0161)**: Minor risk contributor — small code changes may not fully address underlying issues.

**Remediation suggestions**  
- **Investigate and resolve root causes of recent consecutive failures**: Analyze logs for the 7 failed builds to identify recurring issues (e.g., infrastructure, test flakiness).  
- **Stabilize build pipeline before redeploying**: Address systemic issues flagged by high historical failure rates (hist_fail_rate_5, hist_fail_rate_20).  
- **Deploy behind a feature flag or canary**: Limit exposure if redeploying (tie to ROLLBACK decision and high overall risk).  
- **Audit recent commits for quality**: Review the 2 built commits for potential issues (tie to git_num_all_built_commits).  
- **Improve test reliability**: Reduce flakiness in tests contributing to high failure rates (tie to hist_fail_rate_all).
