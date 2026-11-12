# Auth contract

Source of truth for sign-in across `api/`, `infra/` and `web/`. Modelled on Lawata's contract. Change it only on purpose, and update all three packages in the same change.

## Goal
The outage view is public. The engineer risk map and outage detail need an engineer account. The household usage view needs a household account and shows only that household. Accounts are invite-only.

## Provider
- Amazon Cognito user pool in `var.region` (default `ap-southeast-1`). Self sign-up off.
- Groups: `engineers`, `households`.
- Public app client (no secret), authorization code + PKCE, managed login (hosted UI). Scopes `openid email profile`.
- Callback URLs: `http://localhost:5173/auth/callback` and `https://<web_domain>/auth/callback`. Sign-out URLs: the same origins with `/`.

## API auth
- The client sends `Authorization: Bearer <Cognito access token>`.
- The API verifies RS256 against the pool JWKS (cached), `iss` = pool URL, `token_use` = `access`, `client_id` = `COGNITO_CLIENT_ID`, `exp`/`nbf` with 60 s leeway.
- Missing or invalid token: `401 {"detail": "Sign in required"}` + `WWW-Authenticate: Bearer`.
- Valid token, wrong group: `403` (`Engineer access required` or `Household access required`).
- API env: `COGNITO_REGION`, `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID`.
- `AUTH_DISABLED=true` (local dev and tests only) makes every request the `dev` user in both groups. It is refused when `AWS_LAMBDA_FUNCTION_NAME` is set.

## Household identity
- Access tokens carry `sub` but not custom attributes, so the household is resolved **server-side**: `household_account(cognito_sub → sin_hash)` in Neon.
- The `sin_hash` is never accepted from the request or shown to another account.

## Endpoints
| Endpoint | Who |
|---|---|
| `GET /api/health` | public |
| `GET /api/v1/outages?status=open` | public (area rounded to ~110 m, no household data) |
| `GET /api/v1/me` | any signed-in user |
| `GET /api/v1/transformers?bbox=`, `GET /api/v1/transformers/{id}` | `engineers` |
| `GET /api/v1/outages/{id}` | `engineers` |
| `GET /api/v1/me/usage` | `households` |

## Web config (Vite env)
`VITE_AUTH_MODE` = `cognito` | `dev` · `VITE_COGNITO_AUTHORITY` · `VITE_COGNITO_CLIENT_ID` · `VITE_COGNITO_DOMAIN`. `dev` gives a fake user in both groups; pair it with the API's `AUTH_DISABLED=true`.

## Inviting a user
```bash
POOL_ID=$(terraform -chdir=infra/envs/dev output -raw cognito_user_pool_id)
aws cognito-idp admin-create-user --user-pool-id "$POOL_ID" --username jdelacruz \
  --user-attributes Name=email,Value=j.delacruz@example.org Name=email_verified,Value=true
aws cognito-idp admin-add-user-to-group --user-pool-id "$POOL_ID" --username jdelacruz --group-name engineers
```
For a household, add it to `households` instead, then insert its `sub` and `sin_hash` into `household_account` at clamp install.
