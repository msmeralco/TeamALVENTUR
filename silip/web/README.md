# web

Vite + React + TypeScript. Public outage view, engineer risk map and transformer card, household usage view. Run with `make web` (API on :8000 via `make api`).

- `src/features/<name>/` per view; features import `src/shared/` only.
- API types come from FastAPI's OpenAPI: `make schemas` (never hand-written).
- Sign-in: `VITE_AUTH_MODE=dev` locally, `cognito` when deployed (`docs/auth-contract.md`).
