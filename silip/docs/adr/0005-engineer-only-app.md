# 0005. Engineer-only app behind the public landing page

- Status: Accepted
- Date: 2026-11-13

## Context
SILIP is for grid engineers. The web also served residents (public outage check) and households ("My usage"). The owner removed both. The public cinematic landing page stays as the front door (0004). Household clamps still measure load; only the household read path goes away.

## Decision
The web has three parts: the public landing at `/`, sign-in, and the engineer app (decision dashboard, devices, transformer cards). Remove "My usage" and "Outages" from the web. Remove the household API routes `/api/v1/me/usage` and `/api/v1/me/device`. `GET /api/v1/outages` becomes engineer-only. Clamp ingest is unchanged.

## Alternatives considered
- Keep household routes for a future household app: no consumer today, and data minimisation (RA 10173) says do not keep a per-household read path without one.
- Remove the landing too: the owner wants it as the front door.

## Consequences
- Easier: one audience, one nav (Dashboard, Devices), smaller attack surface.
- Harder: residents lose the outage check; the hero's primary action becomes Sign in.
- 0004 is partially superseded: its public `/outages` route no longer exists. The `household_account` table stays (additive schema only).
