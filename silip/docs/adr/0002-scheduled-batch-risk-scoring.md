# 0002. Scheduled batch risk scoring

- Status: Accepted
- Date: 2026-11-12

## Context
The API scored every transformer on its first request and kept the result in a cache that never expired. Clamps publish every 15 minutes (`iot/include/config.h`), so risk only changed on a Lambda cold start.

Measured locally, one process, before this change ("Simulated"):

| Strategies | 50 transformers, 30 days | 2,000 transformers, 14 days |
|---|---|---|
| seasonal_naive + rules | 0.35 s, 194 MB | 7.4 s, 601 MB |
| lightgbm + lightgbm | 1.8 s, 198 MB | 33.7 s, 642 MB |

At 2,000 transformers, lightgbm scoring already exceeds the API Lambda's 30 s timeout. Meralco's transformer count is not in our sources. We assume about 205,000: 8.2M customers (SPEC#sources) divided by the simulator's mean of 40 homes per transformer `[VERIFY]`. Scaling linearly from the 2,000-transformer run: time at 33.7 s / 2,000 = 17 ms per transformer, about 57 min; memory at the marginal (642 − 160 MB process baseline) / 2,000 = 0.24 MB per transformer, about 49 GB. A single Lambda (10,240 MB, 900 s max) tops out near 41,000 transformers on memory and 53,000 on time. Both are estimates from one machine `[VERIFY]` on Lambda.

## Decision
An EventBridge rule invokes a scoring Lambda every 15 minutes. Each run reads the last 14 days of load (`SCORING_WINDOW`, `[VERIFY]`), fits, forecasts 24 h, scores, and inserts the run, its scores and its forecast in one transaction. The API reads the latest completed run. With `DATA_SOURCE=simulated` there is no database, so the API computes on request with a 15-minute cache.

## Alternatives considered
- Score on request with a time-to-live cache everywhere: still blocks the first request for the full scoring time and hits the 30 s timeout at about 2,000 transformers.
- Fit daily, predict every 15 minutes: halves run time at 2,000 transformers (measured per phase: forecaster fit 5.3 s + risk model fit 11.8 s of 33.7 s). It needs model storage (S3 plus deserializing a model) and does not move the first limit, which is memory. Revisit together with sharding.
- Shard by transformer (fan-out to N Lambdas): needed past about 40,000 transformers. Not built yet; the single run holds well past our pilot scale.
- Step Functions or a container task (ECS/Fargate): more moving parts and idle cost for a job that fits one Lambda today.

## Consequences
- Risk follows new readings within one interval, and API reads stay in milliseconds whatever the transformer count.
- Runs are insert-only. A failed run rolls back, so the last good run stays. Reruns for the same 15-minute bucket are skipped.
- Score tables grow by about 97 rows per transformer per run (one score, 96 forecast points). A retention job run by the table owner is needed before long pilots.
- Ingest is the next limit, before scoring: at the assumed scale, one Lambda and one Neon connection per reading means thousands of invocations per second. Follow-up: IoT rule to SQS, batched inserts.
- Cost: one scheduled Lambda, 2,880 runs a month. See the infra report for the estimate `[VERIFY]` against current Lambda pricing.
