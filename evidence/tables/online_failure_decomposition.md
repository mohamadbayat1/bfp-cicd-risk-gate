# Online failure decomposition by previous-build state (the campaign's key finding)

| failure type | count | flagged (p >= tau1) | AUC vs passing builds |
|---|---|---|---|
| continuation (previous build failed) | 30 | 30 / 30 (100%) | 0.936 |
| first-of-streak (previous build passed) | 23 | 0 / 23 (0%) | 0.170 |

Reading: with project history present, the live gate reproduces offline-level strength
(0.936 ~= 0.86 offline). Novel-onset failures — only change-level signal available —
are undetectable (mirrors offline diff-only cross-project AUC 0.5149). The overall 0.60
is the mixture; ~43% of scored failures were novel onsets in this campaign.
