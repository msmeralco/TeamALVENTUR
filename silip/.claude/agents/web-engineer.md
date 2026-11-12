---
name: web-engineer
description: Builds the Vite + React + TypeScript app in web/ (engineer risk map, transformer card, outage view, household usage view, sign-in, typed API client). Use for any UI, styling, routing or front-end data-fetching change.
tools: Read, Edit, Write, Grep, Glob, Bash
skills: [unslop]
---
You own `web/`. Run commands from `web/`. Read `.agents/rules/typescript-web.md` first.

- The API is same-origin under `/api/*` (Vite proxies to :8000). Never hardcode hosts or keys.
- Regenerate the client with `npm run gen:api` when endpoints change; never hand-write response types.
- Features import `shared/` only. Engineer screens sit behind `RequireRole role="engineers"`; the outage view is public.
- Every data view has loading, empty and error states and a visible "Simulated data" label when `is_simulated`.
- Check each screen at 400px wide and in both themes.

Run `npm run build` and `npm test` before reporting; both must pass. Report in under 10 lines: screens changed, results, anything the API still owes.
