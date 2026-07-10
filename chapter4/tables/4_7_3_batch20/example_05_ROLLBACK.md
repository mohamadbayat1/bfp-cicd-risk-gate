# Batch example 5/20 -- decision ROLLBACK, actual fail (correct-catch)

_Model: `nvidia/llama-3.3-nemotron-super-49b-v1.5` via NVIDIA NIM. Real held-out test-set build, test-split row index 135616._

## Input (report_payload, categoricals decoded)

```json
{
  "decision": "ROLLBACK",
  "failure_probability": 0.8668036104081411,
  "thresholds": {
    "tau1": 0.11189963272616212,
    "tau2": 0.4661517258048494
  },
  "top_features": [
    {
      "feature": "hist_consec_fail",
      "value": 86.0,
      "shap": 0.25257627688797757
    },
    {
      "feature": "hist_prev_status",
      "value": 1.0,
      "shap": 0.17717344081151395
    },
    {
      "feature": "hist_fail_rate_5",
      "value": 1.0,
      "shap": 0.12675933678060305
    },
    {
      "feature": "hist_fail_rate_20",
      "value": 1.0,
      "shap": 0.10825486965895155
    },
    {
      "feature": "hist_fail_rate_all",
      "value": 0.45145049691200256,
      "shap": 0.03988988771474229
    },
    {
      "feature": "gh_diff_other_files",
      "value": 6.0,
      "shap": 0.010979911106257543
    }
  ]
}
```

## Ground truth (NOT shown to the model or the LLM)

Actual outcome: **fail** -> correct-catch

## LLM-generated report

1. **Likely cause**  
The build is likely to fail due to a history of recent consecutive failures (hist_consec_fail=86.0, +0.2526 SHAP) and persistent past failures (hist_prev_status=1.0, +0.1772 SHAP), which strongly indicate systemic instability in the codebase or deployment process.  

2. **Contributing factors**  
- **hist_consec_fail=86.0 (+0.2526 SHAP)**  
  *Raises risk*: High count of consecutive failures suggests recurring issues not yet resolved.  
- **hist_prev_status=1.0 (+0.1772 SHAP)**  
  *Raises risk*: Previous build failed, indicating unresolved problems from prior attempts.  
- **hist_fail_rate_5=1.0 (+0.1268 SHAP)**  
  *Raises risk*: Recent 5-build failure rate is perfect (100%), signaling acute instability.  
- **hist_fail_rate_20=1.0 (+0.1083 SHAP)**  
  *Raises risk*: Broader 20-build failure trend remains high (100%), showing chronic issues.  
- **hist_fail_rate_all=0.4515 (+0.0399 SHAP)**  
  *Raises risk*: Long-term failure rate (~45%) is elevated, amplifying risk despite lower SHAP.  
- **gh_diff_other_files=6.0 (+0.0110 SHAP)**  
  *Raises risk slightly*: Changes in multiple files increase deployment complexity and potential for unseen side effects.  

3. **Remediation suggestions**  
- **Stage the deployment behind a feature flag**  
  *Tied to*: hist_consec_fail, hist_prev_status. Mitigate by limiting exposure if failure occurs again.  
- **Address root causes of recent consecutive failures**  
  *Tied to*: hist_consec_fail. Prioritize debugging/reproducing the exact issues causing repeated failures.  
- **Add targeted tests for high-risk areas**  
  *Tied to*: hist_fail_rate_5, hist_fail_rate_20. Improve coverage in modules/files contributing to past failures.  
- **Monitor and rollback mechanisms for multi-file changes**  
  *Tied to*: gh_diff_other_files. Ensure changes in 6+ files are rigorously validated and can be rolled back atomically.  
- **Analyze long-term failure patterns**  
  *Tied to*: hist_fail_rate_all. Investigate systemic issues (e.g., flaky tests, infrastructure instability) over time.
