/** What the map colors: risk tiers (default), clamp coverage, or DOE EV chargers. One at a time. */
export type Overlay = "risk" | "coverage" | "ev";

/** Coverage bands come from the API's own thresholds, so the legend and the action rules agree. */
export interface CoverageBands {
  minTrust: number;
  target: number;
}

/** -1 no clamp data, 0 too few homes reporting to trust, 1 below target, 2 at target. */
export function coverageBand(reporting: number | null | undefined, bands: CoverageBands | null): -1 | 0 | 1 | 2 {
  if (reporting === null || reporting === undefined || bands === null) return -1;
  if (reporting < bands.minTrust) return 0;
  return reporting < bands.target ? 1 : 2;
}

// Charger reach rings only at street zoom, where 1 km is a readable size.
export const RING_MIN_ZOOM = 14;
// Service areas draw from this zoom up.
export const AREA_MIN_ZOOM = 12;
