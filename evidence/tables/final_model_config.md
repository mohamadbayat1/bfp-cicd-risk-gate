# Final model configuration

_Generated: 2026-07-04T14:25:57_

| Component | Value |
|---|---|
| Model | RandomForestClassifier |
| Split criterion | gini |
| Class weighting | balanced |
| Random state / seed | 42 |
| Cross-validation | StratifiedGroupKFold(5) |
| Search criterion | F-beta (beta=2) |
| Search subsample size | 80000 |
| Best CV F-beta (validation-fold mean) | 0.7328 |
| n_estimators (chosen) | 400 |
| max_depth (chosen) | 16 |
| min_samples_leaf (chosen) | 20 |
| max_features (chosen) | 0.4 |
