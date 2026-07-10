# 4-7-5 — Conditional LLM invocation policy test

_Generated: 2026-07-04T19:53:44_

_Policy: the LLM analysis layer is invoked ONLY for WARN/ROLLBACK decisions. PASS builds are skipped entirely -- no LLM call is made, by design, not just by omission. All 3 cases below are real held-out test-set builds (`chapter4/tables/4_7_3_batch20/`), one of each decision state._

## example_09_PASS.md — decision: PASS

**Gate result: SKIPPED.** Decision is PASS -> no LLM call made (policy: only WARN/ROLLBACK trigger the analysis layer). Calibrated failure probability was 0.1011, well under tau1 -- nothing to explain or remediate.

## example_04_WARN.md — decision: WARN

**Gate result: TRIGGERED** (risk margin: close to the ROLLBACK threshold). p(fail)=0.3467.

### LLM-generated report (v2 prompt)

**Summary**  
This build has a moderately elevated failure risk (34.47%) that is close to the rollback threshold, driven by prior build failures, its status as a pull request, and mixed historical reliability signals.  

**Why**  
- The previous build failing raises risk because it suggests unresolved issues in the current pipeline.  
- One consecutive prior failure increases risk as repeated failures often indicate systemic problems.  
- A low overall historical failure rate (7.05%) slightly lowers risk, showing the project generally stabilizes builds.  
- Being a pull request introduces uncertainty due to unmerged code changes not yet validated in main.  
- The previous commit resolving as "build_found" adds minor risk, possibly indicating incomplete cleanup from prior builds.  
- A low recent failure rate (5% in last 20 builds) lowers risk, reflecting improved stability in newer builds.  

**What to do**  
- 🔄 Re-examine the previous failed build to identify and address root causes before retrying.  
- 🔍 Review the pull request changes for potential incompatibilities or missing tests.  
- 📈 Investigate why recent builds (last 20) are more stable to reinforce those improvements.  
- 🧪 Ensure thorough testing of the pull request changes before merging.  

**Technical details**  
- `hist_prev_status`: 1.0 (SHAP +0.1672)  
- `hist_consec_fail`: 1.0 (SHAP +0.1553)  
- `hist_fail_rate_all`: 0.0705 (SHAP -0.0552)  
- `gh_is_pr`: TRUE (SHAP +0.0285)  
- `git_prev_commit_resolution_status`: build_found (SHAP +0.0192)  
- `hist_fail_rate_20`: 0.0500 (SHAP -0.0156)

## example_02_ROLLBACK.md — decision: ROLLBACK

**Gate result: TRIGGERED** (risk margin: just above the ROLLBACK threshold). p(fail)=0.5399.

### LLM-generated report (v2 prompt)

**Summary**  
The build has been rolled back due to a marginally elevated failure risk (53.99% probability), primarily driven by recent build instability and historical failure patterns.  

**Why**  
- The immediately preceding build failed, indicating recent instability.  
- There was one consecutive prior failure, suggesting unresolved issues.  
- Over the last 20 builds, 55% failed, showing recurring problems.  
- The project’s overall failure rate (47.37%) suggests persistent weaknesses.  
- Recent builds (60% failure rate in the last 5) are particularly unstable.  
- The previous commit’s build history resolution being marked as “build found” marginally contributes to uncertainty.  

**What to do**  
- Investigate the root cause of the immediately preceding build failure.  
- Audit recent changes contributing to the high failure rate in the last 5 builds.  
- Review the project’s historical failures to address systemic issues.  
- Verify the resolution status of the previous commit’s build history.  

**Technical details**  
- `hist_prev_status`: 1.0 (SHAP +0.1679)  
- `hist_consec_fail`: 1.0 (SHAP +0.1462)  
- `hist_fail_rate_20`: 0.5500 (SHAP +0.0615)  
- `hist_fail_rate_all`: 0.4737 (SHAP +0.0489)  
- `hist_fail_rate_5`: 0.6000 (SHAP +0.0400)  
- `git_prev_commit_resolution_status`: "build_found" (SHAP +0.0117)

