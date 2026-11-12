# Deploys

## dev, 2026-11-12

- Commit: `53eb337` on `dev`, built from a clean checkout (uncommitted work in the tree was not shipped).
- Web: https://d3kla6q1vf4py1.cloudfront.net
- Cognito user pool: `ap-southeast-1_SIcVK54Ha`. Domain prefix in tfvars is `silip-alventur`; the module appends `-dev`.
- API image: `silip-dev:0.2.0` (API and ingest Lambdas). `DATA_SOURCE=simulated`.
- Applied with `-target` (5 in-place changes plus the scoring log group and role). The scoring Lambda and its schedule were **not** created.
- Smoke test: `/api/health` 200, `/api/v1/outages` 200, `/api/v1/transformers` 401 without a token, SPA routes 200, JS served as `application/javascript`.

### Before the next full apply
1. `infra/modules/api/main.tf`: the scoring Lambda reserves 1 concurrent execution, but the account limit in `ap-southeast-1` is 10 with 10 unreserved, and AWS refuses any reservation below that. Drop the reservation (and guard overlapping runs with a Postgres advisory lock), or raise the quota first.
2. `infra/modules/api/variables.tf`: add `neon` to the `data_source` validation so dev can serve the Neon data (the API already supports it).
3. Restore `infra/envs/prod/.terraform.lock.hcl` (deleted in `f1b50f7`).
4. `maximum_event_age_in_seconds = 900` on the scoring invoke config queues throttled ticks for 15 min; set 60 if they should be dropped.

## dev, 2026-11-12 (fix)

- Image `silip-dev:0.2.1` = `53eb337` plus the uncommitted auth fix below. Commit it so the deployed code has a commit.
- **Fix:** after sign-in every engineer call returned 401. CloudFront signs `/api/*` requests to the Lambda function URL with SigV4 (origin access control), which replaces the browser's `Authorization` header. The web now sends the token in `X-Silip-Authorization`, and the API reads it there first (`api/src/silip/shared/auth/api.py`, `web/src/shared/api/client.ts`, tests in `tests/api/shared/test_auth.py`).
- **Cognito:** the domain is on managed login version 2. Cognito created the default style for the web client when the domain switched; that style is managed outside Terraform for now.
- Checked: a browser signed in through the managed login page as `alventur-solutions`, and `/api/v1/transformers` and `/api/v1/clamps` returned 200.
- The image's `data/sim` came from the working tree at deploy time, which the ML session had regenerated. The risk counts differ from earlier screenshots (28 Critical instead of 13).
