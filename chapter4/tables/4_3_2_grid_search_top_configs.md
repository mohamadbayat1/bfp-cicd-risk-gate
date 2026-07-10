# 4-3-2 — Top grid-search configurations

_Generated: 2026-07-04T14:25:58_

_Full 24-candidate table: `artifacts/grid_search.json`. Search: StratifiedGroupKFold(5), scoring=fbeta(beta=2), subsample n=80000._

| Rank | max_depth | max_features | min_samples_leaf | n_estimators | mean CV F-beta | std |
|---|---|---|---|---|---|---|
| 1 | 16 | 0.4 | 20 | 400 | 0.7328 | 0.0228 |
| 2 | None | 0.4 | 20 | 400 | 0.7323 | 0.0232 |
| 3 | None | 0.4 | 20 | 200 | 0.7322 | 0.0233 |
| 4 | 16 | 0.4 | 20 | 200 | 0.7317 | 0.0231 |
| 5 | 16 | sqrt | 20 | 400 | 0.7313 | 0.0231 |
| 6 | None | sqrt | 20 | 400 | 0.7313 | 0.0227 |
| 7 | None | sqrt | 20 | 200 | 0.7307 | 0.0220 |
| 8 | 16 | sqrt | 20 | 200 | 0.7305 | 0.0230 |
