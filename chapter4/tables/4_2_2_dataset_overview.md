# 4-2-2 — Dataset overview

_Generated: 2026-07-04T14:26:42_

| Quantity | Value |
|---|---|
| Raw records (job level) | 3881992 |
| Builds after aggregation (before dropping `started`) | 925897 |
| Builds after dropping `started` (modeled set) | 925896 |
| Failed builds (y=1: failed/errored/canceled) | 234732 |
| Successful builds (y=0: passed) | 691164 |
| Failure rate | 0.2535 |
| Number of projects | 948 |

## Build status breakdown (4-way, raw `tr_status`)

| Status | Builds | Share |
|---|---|---|
| passed | 691164 | 74.6480% |
| failed | 167204 | 18.0586% |
| errored | 64256 | 6.9399% |
| canceled | 3272 | 0.3534% |
| started | 1 | 0.0001% |

## Failure rate by language (`gh_lang`)

| Language | Builds | Failure rate |
|---|---|---|
| python | 338176 | 0.2389 |
| ruby | 273220 | 0.2759 |
| java | 200561 | 0.2863 |
| go | 113939 | 0.1857 |
