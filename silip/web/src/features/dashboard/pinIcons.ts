import type { Map as MapLibreMap } from "maplibre-gl";

/**
 * Map pin icons: a round badge with a glyph, drawn as SVG and registered with MapLibre as images.
 * The same SVG renders in the legend, so the legend shows exactly what the map draws.
 */

// Path data from lucide-react 1.72 (ISC): `UtilityPole` and `EvCharger`, 24 x 24 viewBox, stroke 2.
// pinIcons.test.tsx checks these against the lucide components, so an upgrade cannot drift silently.
export const UTILITY_POLE_PATHS = [
  "M12 2v20",
  "M2 5h20",
  "M3 3v2",
  "M7 3v2",
  "M17 3v2",
  "M21 3v2",
  "m19 5-7 7-7-7",
] as const;
export const EV_CHARGER_PATHS = [
  "M14 13h2a2 2 0 0 1 2 2v2a2 2 0 0 0 4 0v-6.998a2 2 0 0 0-.59-1.42L18 5",
  "M14 21V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v16",
  "M2 21h13",
  "M3 7h11",
  "m9 11-2 3h3l-2 3",
] as const;

export type Tier = "Critical" | "Watch" | "OK";
export type Theme = "light" | "dark";
export const TIERS: readonly Tier[] = ["Critical", "Watch", "OK"];
export const THEMES: readonly Theme[] = ["light", "dark"];

/** Token values (or `var(--x)` strings for inline SVG) the icons are painted with. */
export interface PinColors {
  critical: string;
  watch: string;
  ok: string;
  card: string;
  foreground: string;
  ring: string;
}

export const TOKEN_VARS: Record<keyof PinColors, string> = {
  critical: "--critical",
  watch: "--watch",
  ok: "--ok",
  card: "--card",
  foreground: "--foreground",
  ring: "--ring",
};

/** For inline SVG in the page: colors follow the theme through CSS variables. */
export const CSS_VAR_COLORS = Object.fromEntries(
  Object.entries(TOKEN_VARS).map(([key, name]) => [key, `var(${name})`]),
) as unknown as PinColors;

/** Every icon is drawn in this square, in CSS px. The badge itself is 32 px across. */
export const ICON_BOX_PX = 40;
const C = ICON_BOX_PX / 2;
const BADGE_R = 15; // plus a 2 px rim: 32 px
const RING_R = 18.5;

const TIER_KEY = { Critical: "critical", Watch: "watch", OK: "ok" } as const;

function glyph(paths: readonly string[], color: string, sizePx: number, strokeWidth: number) {
  const scale = sizePx / 24;
  const offset = C - sizePx / 2;
  const d = paths.map((p) => `<path d="${p}"/>`).join("");
  return (
    `<g transform="translate(${offset} ${offset}) scale(${scale})" style="fill:none;stroke:${color};` +
    `stroke-width:${strokeWidth};stroke-linecap:round;stroke-linejoin:round">${d}</g>`
  );
}

function svg(body: string, sizePx: number) {
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" width="${sizePx}" height="${sizePx}" ` +
    `viewBox="0 0 ${ICON_BOX_PX} ${ICON_BOX_PX}" aria-hidden="true">${body}</svg>`
  );
}

/**
 * A transformer pin: tier-filled badge with a utility pole. Critical also carries a "!" mark at the
 * upper right, so it differs by shape, not by hue alone. Selected adds a `--ring` outline.
 */
export function transformerPinSvg(tier: Tier, colors: PinColors, opts: { selected?: boolean; sizePx?: number } = {}) {
  const fill = colors[TIER_KEY[tier]];
  const ring = opts.selected
    ? `<circle cx="${C}" cy="${C}" r="${RING_R}" style="fill:none;stroke:${colors.ring};stroke-width:3"/>`
    : "";
  const badge = `<circle cx="${C}" cy="${C}" r="${BADGE_R}" style="fill:${fill};stroke:${colors.card};stroke-width:2"/>`;
  const mark =
    tier === "Critical"
      ? `<circle cx="32" cy="8" r="6.5" style="fill:${colors.foreground};stroke:${colors.card};stroke-width:1.5"/>` +
        `<path d="M32 5v3.6M32 11.1v.01" style="fill:none;stroke:${colors.card};stroke-width:2;stroke-linecap:round"/>`
      : "";
  return svg(ring + badge + glyph(UTILITY_POLE_PATHS, colors.card, 18, 2.25) + mark, opts.sizePx ?? ICON_BOX_PX);
}

/** A public EV charger: hollow badge, so it never reads as a transformer. DC stations get a "DC" tag. */
export function chargerPinSvg(dc: boolean, colors: PinColors, opts: { sizePx?: number } = {}) {
  const badge = `<circle cx="${C}" cy="${C}" r="13.5" style="fill:${colors.card};stroke:${colors.foreground};stroke-width:2.5"/>`;
  const tag = dc
    ? `<rect x="21" y="27" width="18" height="12" rx="6" style="fill:${colors.foreground};stroke:${colors.card};stroke-width:1.5"/>` +
      `<text x="30" y="36" text-anchor="middle" style="fill:${colors.card};font:700 8.5px Inter, Arial, sans-serif">DC</text>`
    : "";
  return svg(badge + glyph(EV_CHARGER_PATHS, colors.foreground, 16, 2.25) + tag, opts.sizePx ?? ICON_BOX_PX);
}

/** True when the DOE lists at least one DC connector. Unknown counts are not DC. */
export const isDcCapable = (nDc: number | null | undefined) => typeof nDc === "number" && nDc > 0;

const php = new Intl.NumberFormat([], { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** "PHP 18.00 to 25.50 per kWh", one price if both ends match, or null when the DOE lists none. */
export function priceRange(min: number | null | undefined, max: number | null | undefined): string | null {
  const lo = min ?? max;
  const hi = max ?? min;
  if (lo == null || hi == null) return null;
  return lo === hi ? `PHP ${php.format(lo)} per kWh` : `PHP ${php.format(lo)} to ${php.format(hi)} per kWh`;
}

export const pinImageId = (tier: Tier, theme: Theme, selected = false) =>
  `pin-${tier.toLowerCase()}${selected ? "-selected" : ""}-${theme}`;
export const chargerImageId = (dc: boolean, theme: Theme) => `charger${dc ? "-dc" : ""}-${theme}`;

/** Every image the map needs for one theme: each tier, plain and selected, and both charger kinds. */
export function pinImages(theme: Theme, colors: PinColors): { id: string; svg: string }[] {
  return [
    ...TIERS.flatMap((tier) => [
      { id: pinImageId(tier, theme), svg: transformerPinSvg(tier, colors) },
      { id: pinImageId(tier, theme, true), svg: transformerPinSvg(tier, colors, { selected: true }) },
    ]),
    { id: chargerImageId(false, theme), svg: chargerPinSvg(false, colors) },
    { id: chargerImageId(true, theme), svg: chargerPinSvg(true, colors) },
  ];
}

export type Rasterize = (svg: string, sizePx: number, pixelRatio: number) => Promise<ImageData>;

/** SVG to pixels at the screen's density, through an <img> and a canvas. */
export const rasterizeSvg: Rasterize = async (markup, sizePx, pixelRatio) => {
  const px = Math.round(sizePx * pixelRatio);
  const img = new Image(px, px);
  img.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(markup)}`;
  await img.decode();
  const canvas = document.createElement("canvas");
  canvas.width = px;
  canvas.height = px;
  const ctx = canvas.getContext("2d");
  if (ctx === null) throw new Error("Canvas 2D is not available");
  ctx.drawImage(img, 0, 0, px, px);
  return ctx.getImageData(0, 0, px, px);
};

type ImageTarget = Pick<MapLibreMap, "hasImage" | "addImage" | "updateImage">;

/**
 * Adds (or replaces) every pin image for `theme`. Called after each style load, since a style switch
 * drops the images. Symbols that asked for an image before it arrived redraw once it is added.
 */
export async function registerPinImages(
  map: ImageTarget,
  theme: Theme,
  colors: PinColors,
  pixelRatio: number,
  rasterize: Rasterize = rasterizeSvg,
  isCurrent: () => boolean = () => true,
): Promise<string[]> {
  const images = pinImages(theme, colors);
  const data = await Promise.all(images.map((i) => rasterize(i.svg, ICON_BOX_PX, pixelRatio)));
  if (!isCurrent()) return [];
  images.forEach((image, n) => {
    if (map.hasImage(image.id)) map.updateImage(image.id, data[n]);
    else map.addImage(image.id, data[n], { pixelRatio, sdf: false });
  });
  return images.map((i) => i.id);
}
