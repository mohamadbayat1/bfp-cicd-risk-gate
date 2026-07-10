# Prompt v1 vs v2 comparison -- Commit 6 (real ROLLBACK, GitHub demo)

_Same real payload, same model (`nvidia/llama-3.3-nemotron-super-49b-v1.5` via NVIDIA NIM), only the prompt changed. Risk margin computed for v2: **just above the ROLLBACK threshold**._

## v1 output (original master prompt, 3 sections)

**Likely cause**  
The build is flagged for rollback primarily due to historical indicators of instability: the previous build status (`hist_prev_status=1.0`) and a consecutive failure streak (`hist_consec_fail=1.0`) are the strongest signals, together contributing +0.324 SHAP units to failure risk. These suggest unresolved issues from prior builds compounding the current risk.  

**Contributing factors**  
- `hist_prev_status=1.0` (SHAP +0.1664): A prior failed build state raises risk significantly, indicating unresolved issues.  
- `hist_consec_fail=1.0` (SHAP +0.1576): A streak of consecutive failures amplifies instability concerns.  
- `git_num_all_built_commits=2.0` (SHAP +0.0173): Two commits in this build marginally increase risk, possibly due to scope or interaction complexity.  
- `git_prev_commit_resolution_status=build_found` (SHAP +0.0145): Previous commits resolved via builds (not code fixes) suggest technical debt.  
- `gh_sloc=105.0` (SHAP +0.0143): Moderate code size slightly elevates risk, implying maintenance complexity.  
- `hist_build_seq=4.0` (SHAP +0.0132): The build sequence number 4 has minimal but non-zero risk impact.  

**Remediation suggestions**  
- **Stabilize prior build failures**: Address root causes of previous build failures before retrying (linked to `hist_prev_status` and `hist_consec_fail`).  
- **Split commits**: Reduce `git_num_all_built_commits` by decoupling changes into smaller, isolated builds.  
- **Fix technical debt**: Resolve issues flagged in prior builds (linked to `git_prev_commit_resolution_status`).  
- **Review code complexity**: Audit and simplify the 105 SLOC (`gh_sloc`) to reduce failure hotspots.

## v2 output (developer-facing prompt, 4 sections)

**Summary**  
The build has been flagged for rollback due to a slightly elevated risk of failure (51.3% probability), primarily influenced by recent build history and project maturity factors.  

**Why**  
- The previous build failed, increasing risk slightly.  
- There has been 1 consecutive prior failed build, contributing to uncertainty.  
- This build includes 2 commits, which marginally raises risk compared to smaller batches.  
- The previous commit’s build history was marked as "build_found," adding minor risk.  
- The codebase size is moderate (105 lines), slightly increasing complexity.  
- The project has only had 4 prior builds, indicating lower maturity and higher unpredictability.  

**What to do**  
- Investigate and resolve the cause of the previous build failure before retrying.  
- Reduce commit batch size in future builds to minimize integration risks.  
- Stabilise the build history by ensuring recent commits pass reliably.  
- Monitor project maturity metrics and consider additional testing for new projects.  

**Technical details**  
- hist_prev_status: 1.0 (SHAP +0.1664)  
- hist_consec_fail: 1.0 (SHAP +0.1576)  
- git_num_all_built_commits: 2.0 (SHAP +0.0173)  
- git_prev_commit_resolution_status: "build_found" (SHAP +0.0145)  
- gh_sloc: 105.0 (SHAP +0.0143)  
- hist_build_seq: 4.0 (SHAP +0.0132)
