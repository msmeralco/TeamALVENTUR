# api (`silip`)

FastAPI app served by AWS Lambda (Mangum) behind CloudFront `/api/*`. Run locally with `make api`.

- Features: `transformers` (engineer risk map), `outages` (public list, engineer detail), `household` (own usage), `ingest` (IoT Core → Neon). Layers: `api → adapters → service → domain`.
- `DATA_SOURCE=simulated|clamp|smart_meter` picks where readings come from; models come from `silip_ml` by name.
- Auth: Cognito, see `docs/auth-contract.md`. Local dev: `AUTH_DISABLED=true`.
