/**
 * Pictures for the landing page: the risk map still with its HUD, and the How it works line drawing.
 * Their default render is the final state, so the page reads the same with reduced motion or before
 * landingMotion.ts loads. The data-* hooks are what that module animates.
 */

/**
 * Service areas traced from the still, in its 2880x1800 pixels: the map's own polygons, projected when
 * the still was rendered from TransformerMap (simulated data, centered on T-132, pitch 50, bearing -12).
 */
const CRITICAL_AREA =
  "M1089 852 L1074 897 L1072 944 L1086 991 L1114 1036 L1157 1077 L1213 1112 L1280 1139 L1355 1157 L1435 1163 L1514 1158 L1590 1142 L1659 1117 L1682 1103 L1480 862 L1411 814 L1112 817 Z";
const OK_AREAS = [
  "M1706 583 L1685 551 L1653 522 L1614 497 L1567 477 L1555 474 L1213 522 L1199 670 L1715 613 Z",
  "M1908 828 L1968 857 L2036 878 L2108 892 L2181 897 L2251 893 L2315 881 L2370 860 L2413 833 L2442 800 L2458 763 L2460 725 L2448 687 L2425 650 L2390 615 L2347 584 L2297 558 L2241 537 L2182 521 L2122 511 L2061 508 L2003 511 L1948 520 L1898 534 L1856 555 L1822 581 L1797 611 L1784 645 L1783 682 L1790 705 L1877 801 L1896 820 Z",
  "M1289 -28 L1250 -33 L1208 -35 L1165 -34 L1124 -29 L1084 -22 L1048 -12 L1016 1 L990 16 L972 33 L961 50 L958 69 L965 87 L981 104 L1006 119 L1038 132 L1050 135 L1362 -8 L1358 -10 L1326 -21 Z",
];
// Pins of the OK transformers T-100, T-133 and T-121 in the same pixels. T-132 sits at the exact center.
const OK_PINS: [number, number][] = [
  [1394, 614],
  [2113, 683],
  [1188, 51],
];

export const HUD_LABEL = "Transformer risk, next 24 h";

const MAP_DESCRIPTION =
  "SILIP risk map, simulated data. Transformer T-132 is Critical. Nearby transformers T-100, T-133 and T-121 are OK.";

/**
 * Text that decodes from random letters when landingMotion.ts runs it. The real text is always in the
 * DOM for screen readers and find-in-page; the visible copy is aria-hidden while it scrambles.
 */
export function Decode({ text }: { text: string }) {
  return (
    <>
      <span className="sr-only">{text}</span>
      <span aria-hidden="true" data-decode={text}>
        {text}
      </span>
    </>
  );
}

/** The risk map still, filling its parent. The image and HUD share one box, so the HUD stays on its pins. */
export function HeroMap() {
  return (
    <div role="img" aria-label={MAP_DESCRIPTION} className="absolute inset-0 overflow-hidden">
      <div data-hero-map className="absolute inset-0">
        <div className="hero-drift absolute inset-0">
          <img
            src="/landing/risk-map-2880.webp"
            srcSet="/landing/risk-map-1440.webp 1440w, /landing/risk-map-2880.webp 2880w"
            sizes="(max-aspect-ratio: 8/5) 160vh, 100vw"
            width={2880}
            height={1800}
            // React 18 only passes the lowercase attribute through to the DOM.
            {...{ fetchpriority: "high" }}
            decoding="async"
            alt=""
            className="size-full object-cover opacity-50"
          />
          {/* Desaturates the map when its opacity rises: a gray layer in saturation blend mode. */}
          <div data-hero-mono className="absolute inset-0 bg-stage opacity-0 mix-blend-saturation" />
          <svg
            viewBox="0 0 2880 1800"
            preserveAspectRatio="xMidYMid slice"
            className="absolute inset-0 size-full overflow-visible"
          >
            <path data-hud-line pathLength={1} d={CRITICAL_AREA} className="fill-none stroke-critical stroke-[3]" />
            {OK_AREAS.map((d) => (
              <path key={d} data-hud-line pathLength={1} d={d} className="fill-none stroke-ok stroke-2" />
            ))}
            {OK_PINS.map(([x, y]) => (
              <circle key={x} data-hud-dot cx={x} cy={y} r={11} className="fill-ok" />
            ))}
          </svg>
          {/* The Critical transformer: a ring that pulses in opacity and scale, then its tag. */}
          <span data-hud-pulse className="absolute top-1/2 left-1/2 -translate-1/2">
            <span className="hud-ring absolute inset-0 rounded-full border-2 border-critical" />
            <span className="block size-4 rounded-full border-2 border-stage bg-critical" />
          </span>
          <span
            data-hud-tag
            className="absolute top-1/2 left-1/2 ml-5 -translate-y-1/2 rounded-full bg-critical-soft px-2.5 py-0.5 text-sm font-semibold whitespace-nowrap text-critical"
          >
            Critical · T-132
          </span>
        </div>
      </div>
      <svg aria-hidden="true" data-hero-dots className="absolute inset-0 size-full opacity-0">
        <defs>
          <pattern id="hero-dot-grid" width="32" height="32" patternUnits="userSpaceOnUse">
            <rect x="15" y="15" width="2" height="2" className="fill-stage-grid" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#hero-dot-grid)" />
      </svg>
      {/* landingMotion.ts fills this with square blocks that dissolve the map's edges. */}
      <div data-hero-blocks className="absolute inset-0" />
    </div>
  );
}

/**
 * Pole, transformer and a house with a clamp, drawn one group per How it works step.
 * Every stroke has pathLength 1, so landingMotion.ts can draw it with a dash offset from 1 to 0.
 */
export function LineDrawing() {
  const line = "fill-none stroke-muted-foreground stroke-2 [stroke-linecap:round] [stroke-linejoin:round]";
  return (
    <svg aria-hidden="true" viewBox="0 0 480 400" className="w-full max-w-lg justify-self-center">
      {/* 1. Household clamp: the house, and the clamp on its incoming wire. */}
      <g data-draw-step>
        <path pathLength={1} className={line} d="M20 360 H460" />
        <path pathLength={1} className={line} d="M300 360 V262 L360 212 L420 262 V360" />
        <path pathLength={1} className={line} d="M346 360 V318 H374 V360" />
        <circle pathLength={1} className="fill-none stroke-brand stroke-[3]" cx={300} cy={276} r={10} />
      </g>
      {/* 2. Summed per transformer: the pole, its transformer and the service wire to the house. */}
      <g data-draw-step>
        <path pathLength={1} className={line} d="M120 360 V80" />
        <path pathLength={1} className={line} d="M88 100 H152" />
        <rect pathLength={1} className={line} x={128} y={132} width={40} height={60} rx={10} />
        <path pathLength={1} className={line} d="M152 100 Q 236 186 300 262" />
      </g>
      {/* 3. Load and risk: a load curve over the next 24 hours. */}
      <g data-draw-step>
        <path pathLength={1} className={line} d="M240 160 H460" />
        <path pathLength={1} className={line} d="M240 150 C 280 146 300 96 334 112 S 404 52 460 70" />
      </g>
      {/* 4. Map and outages: a map pin. */}
      <g data-draw-step>
        <path
          pathLength={1}
          className={line}
          d="M60 332 C 42 306 36 298 36 286 A 24 24 0 1 1 84 286 C 84 298 78 306 60 332 Z"
        />
        <circle pathLength={1} className={line} cx={60} cy={286} r={8} />
      </g>
    </svg>
  );
}
