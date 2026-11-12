import type { FeatureCollection, LineString } from "geojson";
import type { Schemas } from "../../shared/api/client";
import { isDcCapable } from "./pinIcons";

type Clamp = Schemas["ClampPoint"];
type Charger = Schemas["Charger"];

const EARTH_RADIUS_M = 6_371_000;
const rad = (deg: number) => (deg * Math.PI) / 180;

/** Great-circle distance in metres. */
export function haversineM(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const a =
    Math.sin(rad(lat2 - lat1) / 2) ** 2 +
    Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(rad(lon2 - lon1) / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.sqrt(a));
}

export interface Links {
  geojson: FeatureCollection<LineString>;
  clamps: number;
  chargers: number;
  dc: number;
}

export const NO_LINKS: Links = { geojson: { type: "FeatureCollection", features: [] }, clamps: 0, chargers: 0, dc: 0 };

/** Lines from one transformer to its own clamps, and from public chargers within `radiusM` to it. */
export function transformerLinks(
  at: { transformer_id: string; lat: number; lon: number } | undefined,
  clamps: Clamp[],
  chargers: Charger[],
  radiusM: number,
): Links {
  if (at === undefined) return NO_LINKS;
  const from = [at.lon, at.lat];
  const own = clamps.filter((c) => c.transformer_id === at.transformer_id);
  const near = radiusM > 0 ? chargers.filter((c) => haversineM(at.lat, at.lon, c.lat, c.lon) <= radiusM) : [];
  return {
    geojson: {
      type: "FeatureCollection",
      features: [
        ...own.map((c) => ({
          type: "Feature" as const,
          geometry: { type: "LineString" as const, coordinates: [from, [c.lon, c.lat]] },
          properties: { kind: "clamp", offline: c.status === "offline", dc: false },
        })),
        ...near.map((c) => ({
          type: "Feature" as const,
          geometry: { type: "LineString" as const, coordinates: [[c.lon, c.lat], from] },
          properties: { kind: "ev", offline: false, dc: isDcCapable(c.n_dc) },
        })),
      ],
    },
    clamps: own.length,
    chargers: near.length,
    dc: near.filter((c) => isDcCapable(c.n_dc)).length,
  };
}
