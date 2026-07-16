# Campaign LLM example — ROLLBACK (bfp-campaign-10 commit #22)

_Generated 2026-07-10T17:12:12.201483+00:00 — real scored campaign build; true positive (the build genuinely failed). Generated with the production prompt (see LLM_PROMPT.md)._

## Input payload (real, categoricals decoded)

```json
{
  "build": "bfp-campaign-10 commit #22",
  "decision": "ROLLBACK",
  "failure_probability": 0.7216133807507952,
  "thresholds": {
    "tau1": 0.11189963272616212,
    "tau2": 0.4661517258048494
  },
  "risk_margin": "well above the ROLLBACK threshold",
  "top_features": [
    {
      "feature": "hist_consec_fail",
      "value": 4.0,
      "shap": 0.26810636097987584
    },
    {
      "feature": "hist_prev_status",
      "value": 1.0,
      "shap": 0.20949277977354314
    },
    {
      "feature": "hist_fail_rate_5",
      "value": 0.800000011920929,
      "shap": 0.06562017639578187
    },
    {
      "feature": "hist_fail_rate_20",
      "value": 0.25,
      "shap": 0.017204837410424022
    },
    {
      "feature": "test_coverage_proxy",
      "value": 111.0,
      "shap": 0.011294808270588935
    },
    {
      "feature": "gh_sloc",
      "value": 543.0,
      "shap": 0.010716314587497333
    }
  ],
  "actual_outcome": "test suite FAILED"
}
```

## LLM-generated report (verbatim)

1. **Summary**  
The build has been assessed as high-risk (72.16% failure probability) and meets rollback criteria due to recurring recent failures and elevated historical failure patterns.  

2. **Why**  
- **Last 4 builds failed consecutively**: Repeated failures strongly indicate unresolved issues in the current pipeline state.  
- **Previous build failed**: A failed prior build increases skepticism about the current build's stability.  
- **80% failure rate in last 5 builds**: Frequent recent failures suggest systemic instability.  
- **25% failure rate in last 20 builds**: Historical instability persists over a longer timeframe.  
- **Test coverage relative to codebase size**: Test coverage may be insufficient for the codebase's scale, exposing undetected risks.  
- **Codebase size (543 lines of code)**: Larger codebases naturally increase complexity and failure risk.  

3. **What to do**  
- Investigate root causes of the 4 consecutive failed builds (e.g., recent code changes, infrastructure issues).  
- Audit test coverage to ensure it adequately addresses the codebase's scale and complexity.  
- Review recent commits for potential fixes to address the high 5-build failure rate.  
- Consider stabilizing the build process before deploying further changes.  

4. **Technical details**  
- hist_consec_fail: 4.0 (SHAP +0.2681)  
- hist_prev_status: 1.0 (SHAP +0.2095)  
- hist_fail_rate_5: 0.800000011920929 (SHAP +0.0656)  
- hist_fail_rate_20: 0.25 (SHAP +0.0172)  
- test_coverage_proxy: 111.0 (SHAP +0.0113)  
- gh_sloc: 543.0 (SHAP +0.0107)
