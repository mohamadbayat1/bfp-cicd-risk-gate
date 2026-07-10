# FINAL.md — online evaluation campaign, final numbers only

_Campaign executed 2026-07-10. Protocol: 9 public GitHub repos (bfp-campaign-02 … 10),
50 real commits each, pushed one at a time; every commit ran the SHADOW risk-gate
workflow (gate records decision, never blocks) followed by the real pytest suite →
every build has a gate decision AND a ground-truth label. Commit sequences are scripted
(seeded, reproducible) with realistic failure clustering: real bugs, imperfect fix
attempts (~45% of fixes fail), unrelated work landing on red builds, streaks capped
at 5. Labels are real test outcomes, never scripted directly. First 20 runs per repo =
warm-up (excluded). Model/calibrator/thresholds identical to the offline evaluation
(τ1 = 0.1119, τ2 = 0.4662). Zero LLM calls during the campaign._

_A 50-commit pilot (bfp-campaign-01, archived in `runs_pilot01_v1generator.csv`) used a
v1 commit generator whose failures never clustered (every break instantly fixed); it
validated the harness end-to-end and exposed that unrealistic failure dynamics invert
the history signal. It is reported as design iteration, not as a result._

## Headline numbers (271 scored builds)

| setting | n | failure rate | ROC-AUC | PR-AUC | Brier |
|---|---|---|---|---|---|
| **online campaign** | 271 | 0.196 | **0.6038** | 0.3886 | 0.1328 |
| offline held-out test (reference) | 138,669 | 0.240 | 0.8602 | 0.7489 | 0.1105 |

## Three-state confusion (actual × decision, scored builds)

| actual \ decision | PASS | WARN | ROLLBACK |
|---|---|---|---|
| pass (n=218) | 174 | 21 | 23 |
| fail (n=53) | 23 | 4 | 26 |

- ROLLBACK precision **0.531** · failures flagged (WARN+ROLLBACK) **56.6%** · false-pass rate **11.7%**
- live-vs-rederived decision mismatches: **0** (the deployed gate applied the saved thresholds exactly)

## The decomposition (the campaign's central finding)

Failures split by whether the previous build had already failed:

| failure type | n | flagged (p ≥ τ1) | AUC vs passing builds | mean p |
|---|---|---|---|---|
| **continuation** (previous build failed) | 30 | **30/30 = 100%** | **0.936** | 0.560 |
| **first-of-streak** (previous build passed) | 23 | **0/23 = 0%** | 0.170 | 0.066 |

The live deployment reproduces both halves of the offline ablation (§۴-۵):
the per-project history signal transfers to a real pipeline at offline-level strength
(0.936 ≈ 0.86 offline), while novel-onset failures — where only diff-level signal
exists — are undetectable (offline diff-only cross-project AUC was 0.515 ≈ random).
The overall 0.60 is the mixture of these two regimes; in this campaign ~43% of scored
failures were novel onsets. Operationally: the gate reliably stops repeated bad
deployments (100% of continuation failures blocked or flagged) and cannot anticipate
the first failure of a streak — matching the framework's design claims and its
documented cold-start/onset limitation.

## Artifacts

- `runs.csv` — all 450 rows (raw evidence; 179 warm-up + 271 scored)
- `campaign_overview.md`, `online_metrics.md` — generated tables (per-repo detail)
- `cold_start_curve.png`, `prob_distribution.png` — the campaign's 2 figures
- Repos: `github.com/novavisionstudio-byte/bfp-campaign-{02..10}` (public, kept as evidence)
- Reproduce: `python campaign/orchestrate.py --repos 9 --start-index 2 --commits 50`
  then `python campaign/score.py` (seeds fixed; labels come from real CI runs)
