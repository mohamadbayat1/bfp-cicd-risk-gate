# AI-Assisted Deployment Risk Gate for CI/CD Pipelines

MSc thesis project: a leakage-free machine-learning framework that predicts, **before a
CI build runs**, the probability it will fail — and maps that probability to a
three-state deployment decision (**PASS / WARN / ROLLBACK**) inside a real CI/CD
pipeline, with a TreeSHAP explainability layer and an LLM-generated developer report.

> **Headline results** — offline (925,896 real TravisTorrent builds, grouped
> cross-project split): **ROC-AUC 0.8602 / PR-AUC 0.7489 / Brier 0.1105**.
> Live online evaluation (450 real GitHub Actions runs, 271 scored):
> continuation failures **30/30 flagged (AUC 0.936)**; novel-onset failures
> undetectable (AUC 0.170) — reproducing the offline ablation in production.
> Central finding: **per-project failure history is the transferable signal;
> diff-level features alone do not generalize across projects (AUC ≈ 0.51).**

## Where the numbers live (single sources of truth)

| file | contents |
|---|---|
| [`RESULTS.md`](RESULTS.md) | full offline workflow + every verified number + reproduction commands |
| [`campaign/results/FINAL.md`](campaign/results/FINAL.md) | online evaluation campaign — final numbers only |
| [`LLM_PROMPT.md`](LLM_PROMPT.md) | the production prompt of the LLM analysis layer (+ exact model id) |
| `chapter4/tables/*.md` | generated evidence tables (never hand-typed; each has a regenerating script) |

## Two-phase architecture

**Offline (this repo — "the factory"):** `run_offline.py` + `bfp/` train the model on
TravisTorrent 2017: dedup to build level → leakage-controlled features (42/66 raw
columns dropped; 6 leakage-free per-project history features) → grouped-by-project
split → RF grid search → Platt calibration → validation-only thresholds
(τ1 = 0.1119, τ2 = 0.4662) → TreeSHAP. Guarded by 9 pytest verification tests
(`pytest -q`).

**Online (separate repos — "the deployed product"):** each deployment repo vendors the
trained model + `bfp` inference code and runs a GitHub Actions **risk-gate job before
the test job**. ROLLBACK genuinely blocks the pipeline (real early stop). The main repo
never runs Actions itself; `campaign/orchestrate.py` generates the deployment repos.

- Demo (blocking gate): `bfp-cicd-risk-gate-demo`
- Evaluation campaign (shadow gate, full Actions run history = the evidence):
  `bfp-campaign-01` (archived pilot), `bfp-campaign-02` … `bfp-campaign-10`
  *(links/account may change after repo transfer; see the Actions tab of each repo
  for the 450 real runs)*

## Reproduce everything

```bash
pip install -r requirements.txt        # pinned versions (python 3.12.10, seed 42)
# place final-2017.csv (TravisTorrent 2017 dump) in the repo root:
# https://travistorrent.testroots.org/
python run_offline.py                  # full offline pipeline (~15 min)
pytest -q                              # 9 leakage/consistency verification tests
python chapter4/scripts/t1_*.py        # regenerate chapter tables/figures
python campaign/orchestrate.py --repos 9 --start-index 2 --commits 50   # online campaign
python campaign/score.py               # score it (warm-up rule, metrics, figures)
```

Large files (dataset 3.5 GB, trained model 317 MB, run CSVs, figures) are deliberately
not committed — everything regenerates deterministically from the commands above.
