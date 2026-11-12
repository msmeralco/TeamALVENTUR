import { render, screen } from "@testing-library/react";
import { EvCharger, UtilityPole } from "lucide-react";
import { describe, expect, it, vi } from "vitest";
import { EvLegend, RiskLegend } from "./MapLegends";
import {
  CSS_VAR_COLORS,
  EV_CHARGER_PATHS,
  THEMES,
  TIERS,
  UTILITY_POLE_PATHS,
  chargerImageId,
  chargerPinSvg,
  isDcCapable,
  pinImageId,
  priceRange,
  registerPinImages,
  transformerPinSvg,
  type PinColors,
} from "./pinIcons";

const COLORS: PinColors = {
  critical: "#c00",
  watch: "#cc0",
  ok: "#0c0",
  card: "#fff",
  foreground: "#111",
  ring: "#08f",
};

const pathsOf = (container: HTMLElement) => [...container.querySelectorAll("path")].map((p) => p.getAttribute("d"));

describe("pin glyphs", () => {
  it("use lucide's own UtilityPole and EvCharger paths", () => {
    expect(pathsOf(render(<UtilityPole />).container)).toEqual([...UTILITY_POLE_PATHS]);
    expect(pathsOf(render(<EvCharger />).container)).toEqual([...EV_CHARGER_PATHS]);
  });

  it("fill each tier with its token and mark only Critical with a shape", () => {
    for (const tier of TIERS) {
      const svg = transformerPinSvg(tier, COLORS);
      expect(svg).toContain(`fill:${COLORS[tier === "OK" ? "ok" : tier === "Watch" ? "watch" : "critical"]}`);
      // The "!" mark is a second circle at the upper right.
      expect(svg.includes('cx="32" cy="8"')).toBe(tier === "Critical");
    }
  });

  it("outline only the selected pin with the ring token", () => {
    expect(transformerPinSvg("OK", COLORS, { selected: true })).toContain(`stroke:${COLORS.ring}`);
    expect(transformerPinSvg("OK", COLORS)).not.toContain(`stroke:${COLORS.ring}`);
  });

  it("tag DC chargers only", () => {
    expect(chargerPinSvg(true, COLORS)).toContain(">DC</text>");
    expect(chargerPinSvg(false, COLORS)).not.toContain("DC");
  });
});

describe("isDcCapable", () => {
  it("needs at least one listed DC connector", () => {
    expect(isDcCapable(2)).toBe(true);
    expect(isDcCapable(0)).toBe(false);
    expect(isDcCapable(null)).toBe(false);
    expect(isDcCapable(undefined)).toBe(false);
  });
});

describe("registerPinImages", () => {
  const fakeMap = () => {
    const images = new Map<string, { pixelRatio?: number; sdf?: boolean }>();
    return {
      images,
      hasImage: (id: string) => images.has(id),
      addImage: vi.fn((id: string, _data: unknown, opts?: { pixelRatio?: number; sdf?: boolean }) => {
        images.set(id, opts ?? {});
      }),
      updateImage: vi.fn(),
    };
  };
  const rasterize = vi.fn(async (_svg: string, size: number, ratio: number) => ({ width: size * ratio }) as ImageData);

  it("adds every tier, plain and selected, and both charger kinds, for each theme", async () => {
    const map = fakeMap();
    for (const theme of THEMES) {
      await registerPinImages(map as never, theme, COLORS, 2, rasterize);
    }
    const expected = THEMES.flatMap((theme) => [
      ...TIERS.flatMap((tier) => [pinImageId(tier, theme), pinImageId(tier, theme, true)]),
      chargerImageId(false, theme),
      chargerImageId(true, theme),
    ]);
    expect([...map.images.keys()].sort()).toEqual(expected.sort());
    for (const opts of map.images.values()) expect(opts).toEqual({ pixelRatio: 2, sdf: false });
  });

  it("replaces images after a style reload instead of adding twice", async () => {
    const map = fakeMap();
    await registerPinImages(map as never, "light", COLORS, 1, rasterize);
    await registerPinImages(map as never, "light", COLORS, 1, rasterize);
    expect(map.addImage).toHaveBeenCalledTimes(8);
    expect(map.updateImage).toHaveBeenCalledTimes(8);
  });

  it("skips a style that was replaced while drawing", async () => {
    const map = fakeMap();
    await registerPinImages(map as never, "dark", COLORS, 1, rasterize, () => false);
    expect(map.addImage).not.toHaveBeenCalled();
  });
});

describe("legends", () => {
  it("name each tier and the Critical mark in words", () => {
    render(<RiskLegend />);
    for (const tier of TIERS) expect(screen.getByText(tier)).toBeTruthy();
    expect(screen.getByText("Critical pins carry a ! mark.")).toBeTruthy();
    expect(screen.getByText("Shaded: estimated service area")).toBeTruthy();
  });

  it("explain the charger pin, the DC tag and the source", () => {
    render(<EvLegend reach="1 km reach" />);
    expect(screen.getByText("Public EV charger, source: DOE")).toBeTruthy();
    expect(screen.getByText("DC tag: has DC fast charging")).toBeTruthy();
    expect(screen.getByText("1 km reach")).toBeTruthy();
  });

  it("paint legend icons with theme variables, not fixed colors", () => {
    expect(transformerPinSvg("Critical", CSS_VAR_COLORS)).toContain("fill:var(--critical)");
  });
});

describe("priceRange", () => {
  it("shows a range, a single price, or nothing", () => {
    expect(priceRange(18, 25.5)).toBe("PHP 18.00 to 25.50 per kWh");
    expect(priceRange(20, 20)).toBe("PHP 20.00 per kWh");
    expect(priceRange(null, 22)).toBe("PHP 22.00 per kWh");
    expect(priceRange(null, null)).toBeNull();
  });
});
