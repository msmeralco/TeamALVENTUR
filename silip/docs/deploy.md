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

## dev, 2026-11-12 (feature/iot merged)

- Commit `ed43b92` on `dev` (merge of `feature/iot`, plus managed login v2). Image `silip-dev:0.3.0`, `DATA_SOURCE=simulated`.
- Full apply (no `-target`): 5 added, 2 changed, 7 destroyed. Removed the IoT Core path (ingest Lambda, role, policy, log group, topic rule, its permission, the `silip-dev-node` IoT policy); devices now post HTTPS through CloudFront to the API Lambda. Added the scoring Lambda (`silip-dev-score`) and its 15-minute EventBridge schedule, without reserved concurrency (account limit 10).
- Neon: the owner ran the `feature/iot` columns (`household.location_label`, `reading.motion`, `clamp.device_key_hash`) and grants.
- Checked: browser sign-in as `alventur-solutions`; `/api/v1/transformers` and `/api/v1/clamps` 200; `/api/health` 200.
- Build tip: build the image from a context with only `pyproject.toml`, `uv.lock`, `ml/`, `api/` and `data/sim` (there is no `.dockerignore`, so a checkout with `.venv` and `node_modules` stalls the upload).

## dev, 2026-11-12 (device management deploy)

- Commits: `b66b109` (API merge repair), `22ab43d` (web routes), `54859e9` (simulated API test fixture).
- API and scoring Lambda image: `silip-dev:0.3.1`; `DATA_SOURCE=simulated`.
- Terraform apply: 0 added, 3 changed, 0 destroyed. Updated both Lambda image URIs and normalized the SPA CloudFront function's line endings.
- Web: https://d3kla6q1vf4py1.cloudfront.net; uploaded with explicit MIME types and immutable caching for hashed assets; invalidation `IBA6L7XNVWMZEAGPC3AV7HT6KZ` completed.
- Smoke checks: `/api/health` 200, `/engineer/devices` 200, new JS bundle served as `application/javascript`; live `/api/*` allows POST.
- Device POST check with the ESP32's `x-amz-content-sha256` header returned 401 `Device key required` because the smoke request intentionally omitted `X-Device-Key`; no reading was stored. The first manual curl omitted the hash header and was rejected by Lambda URL SigV4 validation. The ESP32 HTTP transport already computes and sends this header.
- No database migration was run during this deployment.

## dev, 2026-11-13 (design system + feature/web-polish)

- Commit `c1e8521` on `dev`: the design system (`798b9eb`), the merge repair (`c6ca217`) and `feature/web-polish` merged in. Image `silip-dev:0.4.0` for the API and scoring Lambdas, `DATA_SOURCE=simulated`. It replaces `0.3.3`, which `alejandro` deployed from `feature/web-polish` at 23:44 and did not record here. Everything in `0.3.3` is in `0.4.0`.
- `data/sim` regenerated with `make sim` from the merged notebook, so the dev-only T-Meralco fixture (`577c043`) is in the image: 51 transformers.
- Apply: 0 added, 3 changed, 0 destroyed (both Lambda image tags; the CloudFront SPA function only changed line endings).
- Web built in Cognito mode from the same commit, uploaded file by file with explicit content types. CloudFront `/*` invalidated.
- Smoke test: `/api/health`, `/api/v1/outages` and `/api/v1/bench` 200; `/api/v1/transformers` and `/api/v1/devices` 401 without a token; SPA routes 200; JS served as `application/javascript`; new favicon and brand mark served. Sign-in in a browser was not checked.
- Hygiene: `infra/envs/dev/tfplan-auth` was committed in `cdd1614` and pushed. It is untracked now (`9cafc62`) and `.gitignore` covers `tfplan*`, but it is still in history. The auth module has no client secret, so it likely holds IDs and config only.
- Still open: Cognito managed login still shows the old logo (`docs/cognito-branding/`). `neon` is still missing from the `data_source` validation.
