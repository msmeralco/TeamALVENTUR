# Auth contract

Source of truth for sign-in across `api/`, `infra/` and `web/`. Modelled on Lawata's contract. Change it only on purpose, and update all three packages in the same change.

## Goal
SILIP is an engineer-only app behind a public landing page (ADR 0005). Every data route except the live bench demo needs an engineer account. There is no household read path: `/api/v1/me/usage` and `/api/v1/me/device` were removed. Accounts are invite-only.

## Provider
- Amazon Cognito user pool in `var.region` (default `ap-southeast-1`). Self sign-up off.
- Groups: `engineers`, `households`. No route accepts `households` today; the group stays for clamp installs (see Household identity).
- Public app client (no secret), authorization code + PKCE, managed login (hosted UI). Scopes `openid email profile`.
- Callback URLs: `http://localhost:5173/auth/callback` and `https://<web_domain>/auth/callback`. Sign-out URLs: the same origins with `/`.

## API auth
- The web client sends `X-Silip-Authorization: Bearer <Cognito access token>`. CloudFront signs `/api/*` requests to the Lambda function URL with SigV4 (origin access control), which replaces any viewer `Authorization` header. The API also accepts `Authorization: Bearer` when called directly (local dev, tests).
- The API verifies RS256 against the pool JWKS (cached), `iss` = pool URL, `token_use` = `access`, `client_id` = `COGNITO_CLIENT_ID`, `exp`/`nbf` with 60 s leeway.
- Missing or invalid token: `401 {"detail": "Sign in required"}` + `WWW-Authenticate: Bearer`.
- Valid token, wrong group: `403` (`Engineer access required`).
- API env: `COGNITO_REGION`, `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID`.
- `AUTH_DISABLED=true` (local dev and tests only) makes every request the `dev` user in both groups. It is refused when `AWS_LAMBDA_FUNCTION_NAME` is set.

## Household identity
- The `household_account(cognito_sub → sin_hash)` table stays (additive schema), but no route reads it since the household API was removed (ADR 0005).
- If a household route returns, it must resolve the household **server-side** from the token's `sub`, never accept a `sin_hash` from the request, and never show one account's data to another.

## Endpoints
| Endpoint | Who |
|---|---|
| `GET /api/health` | public |
| `GET /api/v1/bench`, `GET /api/v1/bench/{transformer_id}` | public, live demo only: the bench rig's mock households (`BENCH-*` transformers). The SQL names the bench transformers, and any other ID gets 404. Never a real household. |
| `GET /api/v1/me` | any signed-in user |
| `GET /api/v1/dashboard/summary?bbox=` | `engineers` |
| `GET /api/v1/transformers?bbox=`, `GET /api/v1/transformers/{id}` | `engineers` |
| `GET /api/v1/weather/outlook?bbox=`, `GET /api/v1/ev/chargers?bbox=`, `GET /api/v1/ev/adoption` | `engineers` |
| `GET /api/v1/clamps?bbox=`, `GET /api/v1/clamps/coverage?bbox=` | `engineers` (coverage is counts per transformer, never a device or home) |
| `GET /api/v1/outages?status=open`, `GET /api/v1/outages/{id}` | `engineers` |
| `/api/v1/devices/...` (registry, install, keys) | `engineers` |
| `POST /api/v1/devices/{id}/readings` | the clamp's own device key, not a Cognito token |

The separate, read-only Android PoC route is `GET /mobile-api/v1/devices/{clamp_id}/usage`. It has no user sign-in; the handler returns data only for IDs in `MOBILE_POC_DEVICE_IDS` (`silip-esp32-test` in dev, none in prod). This is not part of the production household-auth contract.

## Web config (Vite env)
`VITE_AUTH_MODE` = `cognito` | `dev` · `VITE_COGNITO_AUTHORITY` · `VITE_COGNITO_CLIENT_ID` · `VITE_COGNITO_DOMAIN`. `dev` gives a fake user in both groups; pair it with the API's `AUTH_DISABLED=true`.

## Inviting a user
```bash
POOL_ID=$(terraform -chdir=infra/envs/dev output -raw cognito_user_pool_id)
aws cognito-idp admin-create-user --user-pool-id "$POOL_ID" --username jdelacruz \
  --user-attributes Name=email,Value=j.delacruz@example.org Name=email_verified,Value=true
aws cognito-idp admin-add-user-to-group --user-pool-id "$POOL_ID" --username jdelacruz --group-name engineers
```
Households get no account today: their clamp reports with its device key.
