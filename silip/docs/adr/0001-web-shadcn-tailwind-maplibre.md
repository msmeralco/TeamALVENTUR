# 0001. Web UI on shadcn/ui + Tailwind, risk map on MapLibre

- Status: Accepted
- Date: 2026-11-12

## Context
The web app used hand-written CSS and an SVG dot plot for the risk map, with no basemap. The owner asked for a calmer, more polished UI built on shadcn/ui, and a real 3D map. Transformer positions now come from OpenStreetMap (`data/osm/README.md`), so a basemap adds real context for engineers.

## Decision
Style `web/` with Tailwind v4 and shadcn/ui components (in `src/shared/ui/components/`). Keep the unslop tokens as the single source of color, renamed to shadcn's variables in `src/shared/styles/tokens.css`; #C2501E is `--critical` only. Draw the risk map with MapLibre GL on OpenFreeMap vector tiles (no API key) with extruded buildings, lazy-loaded so only engineer pages download it.

## Alternatives considered
- Keep plain CSS: fewer dependencies, but every component is hand-built and the owner asked for shadcn.
- MapTiler or Mapbox tiles: nicer styles, but need a key in a `VITE_*` variable (shipped to the browser) and have usage limits.
- Leaflet: lighter, but raster tiles and no 3D buildings.

## Consequences
- New dependencies: tailwindcss, @tailwindcss/vite, class-variance-authority, clsx, tailwind-merge, radix-ui, lucide-react, maplibre-gl; dev: @types/node (for the `@/` path alias in `vite.config.ts`).
- The map chunk is about 1 MB (287 kB gzip), loaded only on `/engineer`.
- The map needs WebGL; tests mock it, and the list beside it carries the same data for keyboard and screen-reader users.
- The page depends on tiles.openfreemap.org being up. Map attribution (OpenFreeMap, OpenMapTiles, OpenStreetMap) stays visible on wide screens; on phones it folds to MapLibre's (i) button so it does not cover the map. If tiles fail, the map says so and the list still has every transformer.
- Tailwind's type scale is limited to four sizes in `global.css` to keep the unslop rule.
- UX polish (2026-11-12) adds `sonner` for toasts (about 10 kB gzip, in the main chunk) and, for tests only, `@testing-library/user-event`. The shadcn CLI also installed an unrelated npm package named `cn` and `next-themes`; both were removed. `Toaster` reads the theme from `src/shared/ui/theme.ts` instead.
- The shadcn components target React 19 (`ref` as a prop). On React 18, `Button` and `AlertDialogOverlay` use `forwardRef`, because Radix passes them refs as menu triggers and dialog parts. Re-check this after adding a component used with `asChild`.
- Risk map layout (2026-11-12): `/engineer` is now a full-screen map with the ranked list in a panel over it (beside it on wide screens, can be hidden; a Show list / Show map toggle on phones, map first). This replaces the earlier list-first phone layout at the owner's request, so the map leads. The list keeps every transformer in words for keyboard and screen-reader users, and on a failed load the panel shows the error and retry on every screen size.
