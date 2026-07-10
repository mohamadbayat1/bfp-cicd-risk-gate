# Prompt v1 vs v2 comparison -- Batch example 9 (real PASS, held-out test set)

_Same real payload, same model (`nvidia/llama-3.3-nemotron-super-49b-v1.5` via NVIDIA NIM), only the prompt changed. Risk margin computed for v2: **just below the WARN threshold**._

## v1 output (original master prompt, 3 sections)

**Likely cause**  
The build is rated PASS (10.1% failure probability) primarily due to **elevated historical failure rates** (hist_fail_rate_all = 0.323, +0.0367 SHAP) and **changes in multiple files** (gh_diff_other_files = 4.0, +0.0201 SHAP), though recent stability (low recent failure rates and no consecutive failures) partially offsets this risk.

**Contributing factors**  
- **hist_fail_rate_all = 0.323** (raises risk): Positive SHAP +0.0367 indicates historical failures increase the model's predicted risk.  
- **gh_diff_other_files = 4.0** (raises risk): Positive SHAP +0.0201 suggests changes in multiple files amplify uncertainty.  
- **hist_fail_rate_20 = 0.05** (lowers risk): Negative SHAP -0.0184 shows recent builds have been more stable, reducing predicted risk.  
- **hist_consec_fail = 0.0** (lowers risk): Negative SHAP -0.0155 suggests no recent consecutive failures improve confidence.  
- **hist_fail_rate_5 = 0.0** (lowers risk): Negative SHAP -0.0150 indicates no recent failures in the last five builds lower risk.  

**Remediation suggestions**  
- **Address historical failures**: Audit and resolve persistent issues in areas with high historical failure rates (linked to hist_fail_rate_all).  
- **Refactor multi-file changes**: Split the current change set into smaller, focused pull requests (linked to gh_diff_other_files) and add targeted tests for modified files.  
- **Preserve recent stability**: Avoid introducing disruptive changes that might break the current streak of successful builds (linked to hist_consec_fail and hist_fail_rate_5).

## v2 output (developer-facing prompt, 4 sections)

**Summary**  
The build passed, but there is a moderate risk of failure (about 10%), slightly below the warning threshold.  

**Why**  
- Historical build failure rate across all builds is high, increasing risk.  
- Multiple non-source files changed in this commit, slightly raising risk.  
- Recent build history shows low failure rate (last 20 builds), reducing risk.  
- No consecutive prior failed builds, lowering risk.  
- Previous commit's build resolution status slightly increases risk.  
- Perfect failure rate in the last 5 builds, significantly lowering risk.  

**What to do**  
- Monitor areas flagged by high historical failure rates (e.g., unstable dependencies).  
- Audit changes to non-source files to ensure they do not introduce edge-case issues.  
- Preserve recent stability by validating changes in critical components.  

**Technical details**  
- `hist_fail_rate_all`: 0.3232 (SHAP +0.0367)  
- `gh_diff_other_files`: 4.0 (SHAP +0.0201)  
- `hist_fail_rate_20`: 0.0500 (SHAP -0.0184)  
- `hist_consec_fail`: 0.0 (SHAP -0.0155)  
- `git_prev_commit_resolution_status`: build_found (SHAP +0.0154)  
- `hist_fail_rate_5`: 0.0 (SHAP -0.0150)
