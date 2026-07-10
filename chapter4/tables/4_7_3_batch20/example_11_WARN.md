# Batch example 11/20 -- decision WARN, actual pass (false-alarm)

_Model: `nvidia/llama-3.3-nemotron-super-49b-v1.5` via NVIDIA NIM. Real held-out test-set build, test-split row index 57665._

## Input (report_payload, categoricals decoded)

```json
{
  "decision": "WARN",
  "failure_probability": 0.19328623087968622,
  "thresholds": {
    "tau1": 0.11189963272616212,
    "tau2": 0.4661517258048494
  },
  "top_features": [
    {
      "feature": "hist_fail_rate_all",
      "value": 0.9038461446762085,
      "shap": 0.06722713948615415
    },
    {
      "feature": "hist_fail_rate_20",
      "value": 0.30000001192092896,
      "shap": 0.05860259312004953
    },
    {
      "feature": "hist_fail_rate_5",
      "value": 0.20000000298023224,
      "shap": 0.03221045882569019
    },
    {
      "feature": "hist_consec_fail",
      "value": 0.0,
      "shap": -0.013118220751692888
    },
    {
      "feature": "hist_build_seq",
      "value": 156.0,
      "shap": -0.010553323601471218
    },
    {
      "feature": "gh_diff_files_added",
      "value": 1.0,
      "shap": 0.010129725404228544
    }
  ]
}
```

## Ground truth (NOT shown to the model or the LLM)

Actual outcome: **pass** -> false-alarm

## LLM-generated report

**Likely cause**  
The build has a 19.3% failure probability (WARN level) primarily due to historical failure patterns: high overall failure rate (**hist_fail_rate_all=90.4%**), moderate 20-build failure rate (**hist_fail_rate_20=30%**), and residual risk from recent changes (**gh_diff_files_added=1**).  

**Contributing factors**  
- **hist_fail_rate_all = 90.4% (SHAP +0.0672)**: Strongly raises risk — indicates systemic instability in past builds.  
- **hist_fail_rate_20 = 30% (SHAP +0.0586)**: Raises risk — recent builds show elevated failure rates.  
- **hist_fail_rate_5 = 20% (SHAP +0.0322)**: Moderately raises risk — recent small failures add uncertainty.  
- **hist_consec_fail = 0 (SHAP -0.0131)**: Lowers risk — no consecutive failures suggest recoverability.  
- **hist_build_seq = 156 (SHAP -0.0106)**: Lowers risk — mature project history provides some stability.  
- **gh_diff_files_added = 1 (SHAP +0.0101)**: Slightly raises risk — small changes may still introduce untested interactions.  

**Remediation suggestions**  
- **Add targeted tests**: Address historical instability (hist_fail_rate_all) with regression tests for high-risk components.  
- **Review recent changes**: Investigate files added/changed (gh_diff_files_added=1) for untested edge cases.  
- **Stabilization sprints**: Reduce overall failure rate (hist_fail_rate_all) through dedicated bug-fixing cycles.  
- **Monitor recent builds**: Track outcomes of builds contributing to hist_fail_rate_20 to identify systemic vs. sporadic issues.
