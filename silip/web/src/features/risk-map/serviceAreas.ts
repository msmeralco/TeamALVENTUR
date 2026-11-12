import { Delaunay } from "d3-delaunay";
import type { FeatureCollection, Polygon, Position } from "geojson";

/**
 * Estimated service areas: each spot goes to its nearest transformer (a Voronoi cell), capped at a radius.
 * Meralco's real secondary-line boundaries are not public, so the UI labels these "estimated".
 */

type Pt = [number, number];

export interface Site {
  transformer_id: string;
  lon: number;
  lat: number;
  tier: string;
}

const METERS_PER_DEG_LAT = 111_320;
const CIRCLE_STEPS = 32;

const cross = (u: Pt, v: Pt) => u[0] * v[1] - u[1] * v[0];
const sub = (a: Pt, b: Pt): Pt => [a[0] - b[0], a[1] - b[1]];

function circle(center: Pt, radius: number): Pt[] {
  // Counter-clockwise, which `clipConvex` expects.
  return Array.from({ length: CIRCLE_STEPS }, (_, i) => {
    const angle = (2 * Math.PI * i) / CIRCLE_STEPS;
    return [center[0] + radius * Math.cos(angle), center[1] + radius * Math.sin(angle)];
  });
}

/** Sutherland-Hodgman: clips `subject` by a convex, counter-clockwise `clip` polygon. */
export function clipConvex(subject: Pt[], clip: Pt[]): Pt[] {
  let output = subject;
  for (let i = 0; i < clip.length && output.length > 0; i++) {
    const a = clip[i];
    const b = clip[(i + 1) % clip.length];
    const edge = sub(b, a);
    const inside = (p: Pt) => cross(edge, sub(p, a)) >= 0;
    const intersect = (p: Pt, q: Pt): Pt => {
      const t = cross(sub(a, p), edge) / cross(sub(q, p), edge);
      return [p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])];
    };
    const input = output;
    output = [];
    input.forEach((current, j) => {
      const previous = input[(j + input.length - 1) % input.length];
      if (inside(current)) {
        if (!inside(previous)) output.push(intersect(previous, current));
        output.push(current);
      } else if (inside(previous)) {
        output.push(intersect(previous, current));
      }
    });
  }
  return output;
}

/** One polygon per site, in lon/lat, with `transformer_id` and `tier` carried as properties. */
export function serviceAreas(sites: Site[], radiusM: number): FeatureCollection<Polygon> {
  if (sites.length === 0) return { type: "FeatureCollection", features: [] };
  // Work in local metres around the centre so distances are even in both directions.
  const lat0 = sites.reduce((sum, s) => sum + s.lat, 0) / sites.length;
  const lon0 = sites.reduce((sum, s) => sum + s.lon, 0) / sites.length;
  const kx = METERS_PER_DEG_LAT * Math.cos((lat0 * Math.PI) / 180);
  const ky = METERS_PER_DEG_LAT;
  const points: Pt[] = sites.map((s) => [(s.lon - lon0) * kx, (s.lat - lat0) * ky]);
  const xs = points.map((p) => p[0]);
  const ys = points.map((p) => p[1]);
  const voronoi = Delaunay.from(points).voronoi([
    Math.min(...xs) - radiusM,
    Math.min(...ys) - radiusM,
    Math.max(...xs) + radiusM,
    Math.max(...ys) + radiusM,
  ]);
  const toLonLat = ([x, y]: Pt): Position => [lon0 + x / kx, lat0 + y / ky];

  return {
    type: "FeatureCollection",
    features: sites.map((site, i) => {
      const reach = circle(points[i], radiusM);
      const cell = voronoi.cellPolygon(i) as Pt[] | null; // null when two sites share a point
      const area = cell === null ? reach : clipConvex(cell.slice(0, -1), reach);
      const ring = area.map(toLonLat);
      return {
        type: "Feature",
        geometry: { type: "Polygon", coordinates: [[...ring, ring[0]]] },
        properties: { transformer_id: site.transformer_id, tier: site.tier },
      };
    }),
  };
}
