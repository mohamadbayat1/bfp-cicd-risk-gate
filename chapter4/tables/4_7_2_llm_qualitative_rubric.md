# 4-7-2 — Qualitative evaluation of the LLM analysis layer

Self-graded rubric over the 2 worked examples in `4_7_1_llm_example_*.md`, both generated
from real SHAP payloads captured from real GitHub Actions runs (commits 2 and 6).

| Criterion | Commit 6 (ROLLBACK) | Commit 2 (PASS) |
|---|---|---|
| Groundedness (no invented metrics/logs/facts) | Pass, after a fix (see below) | Pass |
| Correct SHAP-sign usage (positive=raises, negative=lowers risk) | Correct throughout | Correct throughout |
| Actionability (concrete, feature-tied suggestions) | Concrete (feature flag, split commits, resolve prior failure) | Concrete (smoke tests, canary release) |
| No fourth section / format followed | Followed | Followed |

## A genuine finding: raw label-encoded categoricals cause fabrication

The first pass (before a fix) fed the model the **raw label-encoded integer** for
`git_prev_commit_resolution_status` (e.g. `0.0`) instead of its real category label. The
LLM, given no way to know what `0.0` means for that column, **fabricated a plausible but
wrong interpretation** ("lack of resolution on the previous commit") — exactly the kind of
hallucination the prompt's constraints are meant to prevent, and the prompt's own
groundedness rule did not catch it because the model had no way to know it was guessing.

Fix: decode categorical features back to their saved string labels (via the
preprocessor's `cat_maps_`) before they ever reach the LLM. After the fix, the same
feature (`git_prev_commit_resolution_status = "build_found"`) produced a defensible
reading tied to the actual label. This is a real, reportable limitation of the analysis
layer as specified in `LLM_PROMPT.md`: **the prompt contract must pass human-readable
category labels, not raw encoded integers**, or the "use only the provided data" rule is
not actually enforceable — the model will fill the gap with a guess.

## Notable positive result

Commit 2's report correctly identified `hist_build_seq = 0.0` (no prior builds) as the
single risk-raising feature, and explained it as "no prior builds increase uncertainty" —
independently arriving, in natural language, at the same conclusion as the offline
ablation study (Chapter 4, section 4-5): a project's own history is what the model relies
on, and a brand-new project starting from zero history carries a small inherent risk
premium. This is a good sign the LLM layer surfaces genuine, correct insight rather than
generic boilerplate.

## Limitation of this evaluation

Only 2 real examples were available (no real WARN-decision run occurred among the 6 demo
commits), so this is illustrative, not a statistically powered evaluation.

## Update: superseded by v2 (see `LLM_PROMPT.md`, `tables/4_7_4_v2_comparison_*.md`)

The findings above (groundedness after the categorical-decoding fix, correct SHAP-sign
usage) still hold and are now confirmed across 17 real generations total: the original 2
examples here, 13 more from the held-out test set (`tables/4_7_3_batch20/`), and 2
before/after comparisons. That larger pass surfaced 4 further weaknesses in this v1
prompt (too verbose/jargon-heavy, no confidence calibration near the decision threshold,
inconsistent feature-name translation, one completeness slip) — fixed in **v2**
(`LLM_PROMPT.md`), which is the version to feature in the thesis text going forward. v1
is kept here as the documented starting point of that iteration, not as the final result.
