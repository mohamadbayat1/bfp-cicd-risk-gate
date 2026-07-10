# 4-7-3 — Batch LLM evaluation on real held-out test builds

_Generated: 2026-07-04T19:39:15_

_13 of 20 planned examples completed (the run was stopped after a 180s timeout on a Hermes call for example 14; 13 real, complete examples were judged sufficient for this qualitative pass). Model: `nvidia/llama-3.3-nemotron-super-49b-v1.5` via NVIDIA NIM (Hermes CLI, one-shot). Sampled from the real 138,669-build held-out test split; ground truth (actual pass/fail) was NOT given to the model or the LLM -- shown here only to assess correctness after the fact._

| # | Decision | p(fail) | Actual | Match | Top feature |
|---|---|---|---|---|---|
| 1 | ROLLBACK | 0.5672 | pass | false-alarm | hist_prev_status |
| 2 | ROLLBACK | 0.5399 | fail | correct-catch | hist_prev_status |
| 3 | ROLLBACK | 0.7807 | fail | correct-catch | hist_consec_fail |
| 4 | WARN | 0.3467 | pass | false-alarm | hist_prev_status |
| 5 | ROLLBACK | 0.8668 | fail | correct-catch | hist_consec_fail |
| 6 | WARN | 0.1616 | fail | correct-catch | git_num_all_built_commits |
| 7 | WARN | 0.4651 | pass | false-alarm | hist_prev_status |
| 8 | PASS | 0.0620 | pass | correct-pass | hist_fail_rate_all |
| 9 | PASS | 0.1011 | pass | correct-pass | hist_fail_rate_all |
| 10 | ROLLBACK | 0.8508 | fail | correct-catch | hist_consec_fail |
| 11 | WARN | 0.1933 | pass | false-alarm | hist_fail_rate_all |
| 12 | WARN | 0.1892 | pass | false-alarm | hist_fail_rate_20 |
| 13 | PASS | 0.1037 | pass | correct-pass | hist_fail_rate_20 |

_Decision distribution: {'ROLLBACK': 5, 'WARN': 5, 'PASS': 3}_
_Correctness breakdown: {'false-alarm': 5, 'correct-catch': 5, 'correct-pass': 3}_

Full input+LLM output for each example: `4_7_3_batch20/example_NN_DECISION.md`
