import { describe, expect, it } from "vitest";
import { clipConvex, serviceAreas, type Site } from "./serviceAreas";

type Ring = number[][];

function contains(ring: Ring, [x, y]: [number, number]): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

const site = (id: string, lon: number, lat: number): Site => ({ transformer_id: id, lon, lat, tier: "OK" });
const ringOf = (areas: ReturnType<typeof serviceAreas>, i: number) => areas.features[i].geometry.coordinates[0];

describe("serviceAreas", () => {
  it("gives each transformer its own area that does not reach a neighbour 100 m away", () => {
    const a = site("T-1", 121.0, 14.5);
    const b = site("T-2", 121.0 + 100 / 107_800, 14.5); // about 100 m east at this latitude
    const areas = serviceAreas([a, b], 300);
    expect(areas.features.map((f) => f.properties?.transformer_id)).toEqual(["T-1", "T-2"]);
    expect(contains(ringOf(areas, 0), [a.lon, a.lat])).toBe(true);
    expect(contains(ringOf(areas, 0), [b.lon, b.lat])).toBe(false);
    expect(contains(ringOf(areas, 1), [b.lon, b.lat])).toBe(true);
  });

  it("caps a lone transformer's area at the radius", () => {
    const areas = serviceAreas([site("T-1", 121.0, 14.5), site("T-2", 121.1, 14.6)], 300);
    const farPoint: [number, number] = [121.0 + 400 / 107_800, 14.5]; // 400 m east, past the 300 m cap
    expect(contains(ringOf(areas, 0), farPoint)).toBe(false);
  });

  it("still draws an area when two transformers share a point", () => {
    const areas = serviceAreas([site("T-1", 121.0, 14.5), site("T-2", 121.0, 14.5)], 300);
    expect(areas.features).toHaveLength(2);
    expect(ringOf(areas, 1).length).toBeGreaterThan(3);
  });

  it("returns no areas for no transformers", () => {
    expect(serviceAreas([], 300).features).toEqual([]);
  });
});

describe("clipConvex", () => {
  it("clips a square by a smaller counter-clockwise square", () => {
    const square: [number, number][] = [
      [0, 0],
      [4, 0],
      [4, 4],
      [0, 4],
    ];
    const window: [number, number][] = [
      [1, 1],
      [3, 1],
      [3, 3],
      [1, 3],
    ];
    expect(clipConvex(square, window)).toHaveLength(4);
  });
});
