# Campaign LLM example — WARN (bfp-campaign-07 commit #32)

_Generated 2026-07-10T17:13:42.056161+00:00 — real scored campaign build; true positive (the build genuinely failed). Prompt v2, same workflow as chapter4/tables/4_7_*._

_Provenance note: the first generation attempt returned a serving-tool artifact (the
agent CLI emitted a code-execution TOOLCALL instead of prose); one line — "reply with
the final four-section report as plain markdown text directly; do not use tools or
execute code" — was appended to the prompt for the retry. The prompt contract itself
is unchanged. Wording note: the Summary says "slightly crossing the rollback
consideration threshold" while p=0.406 is in fact below τ2=0.466 (margin string:
"close to the ROLLBACK threshold") — a minor verbal overshoot, preserved verbatim._

## Input payload (real, categoricals decoded)

```json
{
  "build": "bfp-campaign-07 commit #32",
  "decision": "WARN",
  "failure_probability": 0.4058031113261629,
  "thresholds": {
    "tau1": 0.11189963272616212,
    "tau2": 0.4661517258048494
  },
  "risk_margin": "close to the ROLLBACK threshold",
  "top_features": [
    {
      "feature": "hist_prev_status",
      "value": 1.0,
      "shap": 0.17004761430555845
    },
    {
      "feature": "hist_consec_fail",
      "value": 1.0,
      "shap": 0.1537972776695915
    },
    {
      "feature": "gh_repo_age",
      "value": 0.02846391499042511,
      "shap": -0.018862335626667837
    },
    {
      "feature": "git_prev_commit_resolution_status",
      "value": "build_found",
      "shap": 0.015769042513138345
    },
    {
      "feature": "hist_fail_rate_5",
      "value": 0.20000000298023224,
      "shap": 0.012704330264642323
    },
    {
      "feature": "hist_fail_rate_20",
      "value": 0.3499999940395355,
      "shap": 0.012150917882717351
    }
  ],
  "actual_outcome": "test suite FAILED"
}
```

## LLM-generated report (verbatim)

**Summary**  
This build has a moderate risk of failure (40.58%) that is marginally elevated due to recent instability patterns, slightly crossing the rollback consideration threshold.  

**Why**  
- The previous build failed, increasing the likelihood of recurring issues.  
- A prior streak of 1 consecutive failed build suggests unresolved problems.  
- The repository's age is relatively stable, which slightly reduces risk.  
- The last commit's resolution involved marking a build as "found," introducing minor uncertainty.  
- The 20% failure rate over the last 5 builds and 35% over 20 builds indicate historically mixed reliability.  

**What to do**  
- Investigate the root cause of the previous build failure to address recurring issues.  
- Review test coverage and fix flakiness given the elevated recent failure rate.  
- Audit the resolution process for the last commit to ensure no hidden issues remain.  
- Monitor repository stability over time despite its maturity.  

**Technical details**  
- `hist_prev_status`: 1.0 (SHAP +0.1700)  
- `hist_consec_fail`: 1.0 (SHAP +0.1538)  
- `gh_repo_age`: 0.02846 (SHAP -0.0189)  
- `git_prev_commit_resolution_status`: "build_found" (SHAP +0.0158)  
- `hist_fail_rate_5`: 0.20000 (SHAP +0.0127)  
- `hist_fail_rate_20`: 0.35000 (SHAP +0.0122)
