# api (`silip`)

FastAPI app served by AWS Lambda (Mangum) behind CloudFront `/api/*`. Run locally with `make api`.

- Features: `transformers` (engineer risk map), `outages` (public list, engineer detail), `household` (own usage), `devices` (dashboard registration and assignment), `ingest` (device-key HTTP reports → database). Layers: `api → adapters → service → domain`.
- `DATA_SOURCE=simulated|neon|clamp|smart_meter` picks where readings come from; models come from `silip_ml` by name.
- Auth: Cognito, see `docs/auth-contract.md`. Local dev: `AUTH_DISABLED=true`.

Device registration: `docs/iot-management.md`. Device keys are independent of Cognito; only engineers can issue or replace them.
