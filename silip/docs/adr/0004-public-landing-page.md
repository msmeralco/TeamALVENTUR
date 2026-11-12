# 0004. Public landing page at `/`, outages at `/outages`

- Status: Partially superseded by 0005
- Date: 2026-11-13

## Context
`/` opened straight onto the outage list. A first-time visitor (a resident, an engineer or a hackathon judge) never learned what SILIP is or who it is for. Signed-out visitors also saw engineer and household tabs that led to a sign-in wall. The outage check is still the most common public task, so it cannot move behind a click.

## Decision
`/` becomes a public landing page whose hero is the outage check itself (search and "Near me", results inline). The full outage list moves to `/outages`. Old links with query strings on `/` redirect to `/outages` with the query kept. `/demo` stays unlisted and is marked `noindex`.

## Alternatives considered
- Keep `/` as the outage list and add an "About" page: visitors still land without context, and few would open About.
- Landing page with the outage list one click away: adds a step to the most common public task. (Hick's Law)

## Consequences
- Easier: one page explains SILIP and answers "is my power out?"; signed-out navigation shows only what a visitor can use.
- Harder: two routes render outage results, so the search and result cards live in one component in `features/outages/` and are composed into the landing page from `app/`.
- Watch: links already shared (QR codes, slides, the demo video) that point at `/` with outage queries. The redirect covers them.
