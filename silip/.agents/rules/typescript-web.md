# TypeScript / web rules (`web/`)

On top of [engineering-standards.md](engineering-standards.md). Visual rules come from the `unslop` skill.

## Stack
- Vite + React + TypeScript `strict`. No `any`, no `@ts-ignore`.
- `react-router` for routes, TanStack Query for server state (no fetching inside `useEffect`).
- API client: `openapi-fetch`, typed by `openapi-typescript` from FastAPI's OpenAPI (`src/shared/api/schema.ts`, generated, never edited). Calls go to same-origin `/api/*`; Vite proxies to :8000 in dev.

## Layout
```
web/src/
  app/              routes, Shell, providers, AuthCallbackPage
  shared/           api/ (client + schema), auth/, ui/, styles/tokens.css
  features/<name>/  components + hooks for one feature (risk-map, transformer-card, outages, household)
```
Features import from `shared/` only, never from each other.

## Styling
- Tokens from `unslop` as CSS variables on `:root` (light is the default); dark overrides under `[data-theme="dark"]`. No hardcoded colors in components.
- Mobile-first; works at 400px with no horizontal scroll.
- No accent bars or colored edge lines on rows or cards; use hairlines and type size.
- Status = color + word (OK, Watch, Critical). Show coverage and confidence beside risk.

## Every data view
- Loading, empty and error (with retry) states, each with a short plain message.
- Simulated data shows a visible "Simulated data" label.

## Auth
- `VITE_AUTH_MODE=cognito|dev`. Sessions live in `sessionStorage` through `oidc-client-ts` in `shared/auth`, never in `localStorage`.
- No secrets in `VITE_*` variables.

## Check
`npm run build` (type check included) and `npm test` pass before reporting.
