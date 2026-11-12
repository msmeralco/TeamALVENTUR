import type {
  ExpressionSpecification,
  GeoJSONSource,
  LngLatBoundsLike,
  MapLayerMouseEvent,
  MapMouseEvent,
  Map as MapLibreMap,
} from "maplibre-gl";
import { GeolocateControl } from "maplibre-gl";
import type { FeatureCollection, Point, Polygon } from "geojson";
import { Maximize2, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type ReactNode, type RefObject } from "react";
import type { Schemas } from "../../shared/api/client";
import { byQueue, reportAge, type ClampCount } from "../../shared/risk";
import { ActionBadge, SimulatedLabel, TierBadge, cn, formatPct } from "../../shared/ui";
import { Badge } from "../../shared/ui/components/badge";
import { Button } from "../../shared/ui/components/button";
import { Map, cssVar, fitOptions, isAlive, prefersDark } from "../../shared/ui/components/map";
import { AREA_MIN_ZOOM, RING_MIN_ZOOM, coverageBand, type CoverageBands, type Overlay } from "./overlays";
import {
  TOKEN_VARS,
  chargerImageId,
  isDcCapable,
  priceRange,
  pinImageId,
  registerPinImages,
  type PinColors,
  type Theme,
  type Tier,
} from "./pinIcons";
import { serviceAreas } from "./serviceAreas";
import { transformerLinks, type Links } from "./links";

type Item = Schemas["TransformerRisk"];
type Clamp = Schemas["ClampPoint"];
type Charger = Schemas["Charger"];

/** Clamp devices of the shown transformers, as points. Status only; no household identity or usage. */
function clampsGeoJson(clamps: Clamp[], shown: ReadonlySet<string>): FeatureCollection<Point> {
  return {
    type: "FeatureCollection",
    features: clamps
      .filter((c) => shown.has(c.transformer_id))
      .map((c) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [c.lon, c.lat] },
        properties: { clamp_id: c.clamp_id, status: c.status },
      })),
  };
}

const PINS = "transformers";
const CLAMPS = "clamps";
const AREAS = "service-areas";
const CHARGERS = "ev-chargers";
const CHARGER_RINGS = "ev-charger-rings";
const LINKS = "selected-links";
const LAYER = {
  areaFill: "service-area-fill",
  areaVolume: "service-area-volume",
  areaOutline: "service-area-outline",
  clusters: "transformer-clusters",
  clusterCount: "transformer-cluster-count",
  pins: "transformer-pins",
  pinActive: "transformer-pin-active",
  pinSelected: "transformer-pin-selected",
  pinLabels: "transformer-pin-labels",
  clamps: "clamp-points",
  coverageFill: "coverage-fill",
  coverageOutline: "coverage-outline",
  chargers: "ev-charger-points",
  chargerRings: "ev-charger-rings",
  linkClamp: "link-clamp",
  linkClampOffline: "link-clamp-offline",
  linkEv: "link-ev",
} as const;

const OVERLAY_LAYERS: Record<Overlay, string[]> = {
  risk: [LAYER.areaFill, LAYER.areaVolume, LAYER.areaOutline],
  coverage: [LAYER.coverageFill, LAYER.coverageOutline],
  ev: [LAYER.chargers, LAYER.chargerRings],
};
const RING_STEPS = 48;
const METERS_PER_DEG_LAT = 111_320;
// Sequential, neutral to sage: low coverage stays gray (a warning is never green), more homes reporting reads greener.
const COVERAGE_FILL_OPACITY = { none: 0, low: 0.18, mid: 0.28, high: 0.55 } as const;

// Estimated reach of one transformer's secondary lines. [VERIFY] with Meralco distribution standards.
const SERVICE_RADIUS_M = 300;
const CLUSTER_MAX_ZOOM = 12; // above this, areas and single pins take over
const CLUSTER_RADIUS_PX = 48;
const VOLUME_MIN_ZOOM = 14; // matches where 3D buildings appear
const VOLUME_HEIGHT_M = 40; // visual tint over buildings only, not data
const LABEL_MIN_ZOOM = 14;
const LABEL_FONT = ["Noto Sans Regular"]; // shipped by both OpenFreeMap styles
const TIER_RANK = { OK: 0, Watch: 1, Critical: 2 } as const;
// Pins are 32 px badges; the hovered or selected one grows so it stands out by size, not only by its ring.
const ACTIVE_ICON_SCALE = 1.25;
const LABEL_SIZE_PX = 12;
// Full-size badges from street zoom; smaller between the clusters and the streets, where pins crowd.
const PIN_FULL_ZOOM = 15;
const PIN_SMALL_SCALE = 0.6;
const pinSize = (scale: number): ExpressionSpecification => [
  "interpolate",
  ["linear"],
  ["zoom"],
  CLUSTER_MAX_ZOOM,
  PIN_SMALL_SCALE * scale,
  PIN_FULL_ZOOM,
  scale,
];
const LABEL_OFFSET_EM = 1.6; // just below the 32 px badge
const CLAMP_MIN_ZOOM = 15; // single homes are only readable at street level
// Opens at street level on the most urgent transformer, so 3D buildings (14+) and clamps (15+) show at once.
const START_ZOOM = 15.5;
const CLAMP_RADIUS_PX = 2.5;
const CLAMP_SELECTED_RADIUS_PX = 5;
// A tap within this many px of a pin picks it: the 32 px badge with a mouse, a 44 px target on touch.
const tapTolerancePx = () =>
  typeof window.matchMedia === "function" && window.matchMedia("(pointer: coarse)").matches ? 22 : 16;
const FOCUS_ZOOM = 15.5; // show the transformer label and nearby clamp points
const EASE_MS = 600;
const MAP_PADDING_PX = 48;
// Critical areas get a stronger fill and outline than Watch, so they differ by more than hue in both themes.
const AREA_FILL_OPACITY = { Critical: 0.34, Watch: 0.18, OK: 0.1 } as const;
const AREA_LINE_WIDTH = { Critical: 2.5, Watch: 1.25, OK: 0.75 } as const;

function geolocateFitOptions(leftInsetPx: number) {
  return {
    maxZoom: FOCUS_ZOOM,
    padding: {
      top: MAP_PADDING_PX,
      right: MAP_PADDING_PX,
      bottom: MAP_PADDING_PX,
      left: MAP_PADDING_PX + leftInsetPx,
    },
  };
}

function byTier(values: Record<"Critical" | "Watch" | "OK", number>): ExpressionSpecification {
  return ["match", ["get", "tier"], "Critical", values.Critical, "Watch", values.Watch, values.OK];
}

const isActive: ExpressionSpecification = ["boolean", ["feature-state", "active"], false];
const isSelected: ExpressionSpecification = ["boolean", ["feature-state", "selected"], false];

function tierColor(tier: ExpressionSpecification): ExpressionSpecification {
  return ["match", tier, "Critical", cssVar("--critical"), "Watch", cssVar("--watch"), cssVar("--ok")];
}

/** Worst tier in a cluster, from the summed-up `worst` rank. */
const clusterColor: ExpressionSpecification = [
  "match",
  ["get", "worst"],
  TIER_RANK.Critical,
  cssVar("--critical"),
  TIER_RANK.Watch,
  cssVar("--watch"),
  cssVar("--ok"),
];

const themeNow = (): Theme => (prefersDark() ? "dark" : "light");

const tokenColors = (): PinColors =>
  Object.fromEntries(Object.entries(TOKEN_VARS).map(([key, name]) => [key, cssVar(name)])) as unknown as PinColors;

function pinImage(theme: Theme, selected = false): ExpressionSpecification {
  const id = (tier: Tier) => pinImageId(tier, theme, selected);
  return ["match", ["get", "tier"], "Critical", id("Critical"), "Watch", id("Watch"), id("OK")];
}

const onlyId = (id: string | null): ExpressionSpecification => ["==", ["get", "transformer_id"], id ?? ""];

/** Labels for every single pin except the hovered and selected ones, which carry their own. */
const labelFilter = (activeId: string | null, selectedId: string | null): ExpressionSpecification => [
  "all",
  ["!", ["has", "point_count"]],
  ["!", onlyId(activeId)],
  ["!", onlyId(selectedId)],
];

const labelPaint = () => ({
  "text-color": cssVar("--foreground"),
  "text-halo-color": cssVar("--card"),
  "text-halo-width": 1.5,
});

function pinsGeoJson(items: Item[]): FeatureCollection<Point> {
  return {
    type: "FeatureCollection",
    features: items.map((i) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [i.lon, i.lat] },
      properties: { transformer_id: i.transformer_id, tier: i.risk.tier, rank: TIER_RANK[i.risk.tier] },
    })),
  };
}

function areasGeoJson(items: Item[], shown: ReadonlySet<string>, bands: CoverageBands | null) {
  const all = serviceAreas(
    items.map((i) => ({ transformer_id: i.transformer_id, lon: i.lon, lat: i.lat, tier: i.risk.tier })),
    SERVICE_RADIUS_M,
  );
  const band = new globalThis.Map(
    items.map((i) => [i.transformer_id, coverageBand(i.clamp_health?.reporting_pct, bands)]),
  );
  // Cells come from every transformer, so filtering never stretches a cell; only the shown ones are drawn.
  return {
    ...all,
    features: all.features
      .filter((f) => shown.has(f.properties?.transformer_id))
      .map((f) => ({ ...f, properties: { ...f.properties, cov: band.get(f.properties?.transformer_id) ?? -1 } })),
  };
}

function chargersGeoJson(chargers: Charger[]): FeatureCollection<Point> {
  return {
    type: "FeatureCollection",
    features: chargers.map((c) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [c.lon, c.lat] },
      properties: { station_id: c.station_id, dc: isDcCapable(c.n_dc) },
    })),
  };
}

/** A circle of `radiusM` around each charger, as a polygon, so it scales with the map. */
function ringsGeoJson(chargers: Charger[], radiusM: number): FeatureCollection<Polygon> {
  return {
    type: "FeatureCollection",
    features: chargers.map((c) => {
      const dLat = radiusM / METERS_PER_DEG_LAT;
      const dLon = dLat / Math.cos((c.lat * Math.PI) / 180);
      const ring = Array.from({ length: RING_STEPS + 1 }, (_, i) => {
        const angle = (2 * Math.PI * (i % RING_STEPS)) / RING_STEPS;
        return [c.lon + dLon * Math.cos(angle), c.lat + dLat * Math.sin(angle)];
      });
      return { type: "Feature", geometry: { type: "Polygon", coordinates: [ring] }, properties: {} };
    }),
  };
}

function applyOverlay(map: MapLibreMap, overlay: Overlay) {
  for (const [name, layers] of Object.entries(OVERLAY_LAYERS)) {
    for (const layer of layers) {
      if (map.getLayer(layer)) map.setLayoutProperty(layer, "visibility", name === overlay ? "visible" : "none");
    }
  }
}

const shownPins = (items: Item[], shown: ReadonlySet<string>) =>
  pinsGeoJson(items.filter((i) => shown.has(i.transformer_id)));

function boundsOf(items: Item[]): LngLatBoundsLike {
  const lons = items.map((i) => i.lon);
  const lats = items.map((i) => i.lat);
  return [Math.min(...lons), Math.min(...lats), Math.max(...lons), Math.max(...lats)];
}

/** City zoom: clusters ringed in their worst tier. Street zoom: shaded service areas, pins and IDs. */
function addLayers(
  map: MapLibreMap,
  items: Item[],
  shown: ReadonlySet<string>,
  clamps: Clamp[],
  bands: CoverageBands | null,
  chargers: Charger[],
  ringRadiusM: number,
  theme: Theme,
  activeId: string | null,
  selectedId: string | null,
  links: Links,
) {
  // CSS variables are read here, not at import time, so each style load follows the current theme.
  const tier = tierColor(["get", "tier"]);
  map.addSource(AREAS, { type: "geojson", data: areasGeoJson(items, shown, bands), promoteId: "transformer_id" });
  map.addSource(PINS, {
    type: "geojson",
    data: shownPins(items, shown),
    promoteId: "transformer_id",
    cluster: true,
    clusterMaxZoom: CLUSTER_MAX_ZOOM,
    clusterRadius: CLUSTER_RADIUS_PX,
    clusterProperties: { worst: ["max", ["get", "rank"]] },
  });

  map.addLayer({
    id: LAYER.areaFill,
    type: "fill",
    source: AREAS,
    minzoom: AREA_MIN_ZOOM,
    paint: { "fill-color": tier, "fill-opacity": ["case", isActive, 0.5, byTier(AREA_FILL_OPACITY)] },
  });
  map.addLayer({
    id: LAYER.areaVolume,
    type: "fill-extrusion",
    source: AREAS,
    minzoom: VOLUME_MIN_ZOOM,
    paint: { "fill-extrusion-color": tier, "fill-extrusion-height": VOLUME_HEIGHT_M, "fill-extrusion-opacity": 0.2 },
  });
  map.addLayer({
    id: LAYER.areaOutline,
    type: "line",
    source: AREAS,
    minzoom: AREA_MIN_ZOOM,
    paint: { "line-color": tier, "line-width": ["case", isActive, 3.5, byTier(AREA_LINE_WIDTH)] },
  });
  map.addLayer({
    id: LAYER.coverageFill,
    type: "fill",
    source: AREAS,
    minzoom: AREA_MIN_ZOOM,
    layout: { visibility: "none" },
    paint: {
      "fill-color": ["match", ["get", "cov"], 0, cssVar("--muted-foreground"), cssVar("--brand")],
      "fill-opacity": [
        "match",
        ["get", "cov"],
        0,
        COVERAGE_FILL_OPACITY.low,
        1,
        COVERAGE_FILL_OPACITY.mid,
        2,
        COVERAGE_FILL_OPACITY.high,
        COVERAGE_FILL_OPACITY.none,
      ],
    },
  });
  map.addLayer({
    id: LAYER.coverageOutline,
    type: "line",
    source: AREAS,
    minzoom: AREA_MIN_ZOOM,
    layout: { visibility: "none" },
    paint: { "line-color": cssVar("--muted-foreground"), "line-width": ["case", isActive, 3, 0.75] },
  });
  // The selected transformer's links: thin brand lines to its clamps (dashed, muted when offline), and dotted
  // lines in the charger color from chargers within reach (heavier for DC). Under the chargers and pins.
  map.addSource(LINKS, { type: "geojson", data: links.geojson });
  map.addLayer({
    id: LAYER.linkClamp,
    type: "line",
    source: LINKS,
    filter: ["all", ["==", ["get", "kind"], "clamp"], ["!", ["get", "offline"]]],
    paint: { "line-color": cssVar("--brand"), "line-width": 1.25, "line-opacity": 0.9 },
  });
  map.addLayer({
    id: LAYER.linkClampOffline,
    type: "line",
    source: LINKS,
    filter: ["all", ["==", ["get", "kind"], "clamp"], ["get", "offline"]],
    paint: {
      "line-color": cssVar("--muted-foreground"),
      "line-width": 1.25,
      "line-opacity": 0.7,
      "line-dasharray": [2, 2],
    },
  });
  map.addLayer({
    id: LAYER.linkEv,
    type: "line",
    source: LINKS,
    filter: ["==", ["get", "kind"], "ev"],
    layout: { "line-cap": "round" },
    paint: {
      "line-color": cssVar("--foreground"),
      "line-width": ["case", ["get", "dc"], 2.5, 1.5],
      "line-opacity": 0.75,
      "line-dasharray": [0.5, 2.5],
    },
  });
  map.addSource(CHARGER_RINGS, { type: "geojson", data: ringsGeoJson(chargers, ringRadiusM) });
  map.addSource(CHARGERS, { type: "geojson", data: chargersGeoJson(chargers) });
  map.addLayer({
    id: LAYER.chargerRings,
    type: "line",
    source: CHARGER_RINGS,
    minzoom: RING_MIN_ZOOM,
    layout: { visibility: "none" },
    paint: { "line-color": cssVar("--foreground"), "line-opacity": 0.8, "line-width": 2, "line-dasharray": [3, 2] },
  });
  map.addLayer({
    id: LAYER.chargers,
    type: "symbol",
    source: CHARGERS,
    // Hollow badge with a charger glyph, so a charger never reads as a transformer. DC stations carry a tag.
    layout: {
      visibility: "none",
      "icon-image": ["case", ["get", "dc"], chargerImageId(true, theme), chargerImageId(false, theme)],
      "icon-allow-overlap": true,
    },
  });
  // Same badge family as the pins: filled with the worst tier inside, count in the card color.
  map.addLayer({
    id: LAYER.clusters,
    type: "circle",
    source: PINS,
    filter: ["has", "point_count"],
    paint: {
      "circle-color": clusterColor,
      "circle-stroke-color": cssVar("--card"),
      "circle-stroke-width": 2,
      "circle-radius": ["step", ["get", "point_count"], 16, 5, 20, 15, 26],
    },
  });
  map.addLayer({
    id: LAYER.clusterCount,
    type: "symbol",
    source: PINS,
    filter: ["has", "point_count"],
    layout: { "text-field": ["get", "point_count_abbreviated"], "text-font": LABEL_FONT, "text-size": 13 },
    paint: { "text-color": cssVar("--card") },
  });
  map.addSource(CLAMPS, { type: "geojson", data: clampsGeoJson(clamps, shown), promoteId: "clamp_id" });
  map.addLayer({
    id: LAYER.clamps,
    type: "circle",
    source: CLAMPS,
    minzoom: CLAMP_MIN_ZOOM,
    paint: {
      "circle-radius": ["case", isSelected, CLAMP_SELECTED_RADIUS_PX, CLAMP_RADIUS_PX],
      "circle-color": ["match", ["get", "status"], "online", cssVar("--muted-foreground"), cssVar("--card")],
      // 4. the dot the popover describes gets a foreground ring
      "circle-stroke-color": ["case", isSelected, cssVar("--foreground"), cssVar("--muted-foreground")],
      "circle-stroke-width": ["case", isSelected, 3, 1.25],
    },
  });
  // Labels give way to each other, Critical first, and draw under the pins, so a pin is never covered.
  // A hovered or selected pin draws its own label further down.
  map.addLayer({
    id: LAYER.pinLabels,
    type: "symbol",
    source: PINS,
    minzoom: LABEL_MIN_ZOOM,
    filter: labelFilter(activeId, selectedId),
    layout: {
      "text-field": ["get", "transformer_id"],
      "text-font": LABEL_FONT,
      "text-size": LABEL_SIZE_PX,
      "text-offset": [0, LABEL_OFFSET_EM],
      "text-anchor": "top",
      "symbol-sort-key": ["-", 0, ["get", "rank"]],
    },
    paint: labelPaint(),
  });
  // Every pin always shows (a hidden Critical pin would be a miss); worse tiers draw on top.
  map.addLayer({
    id: LAYER.pins,
    type: "symbol",
    source: PINS,
    filter: ["!", ["has", "point_count"]],
    layout: {
      "icon-image": pinImage(theme),
      "icon-size": pinSize(1),
      "icon-allow-overlap": true,
      "icon-ignore-placement": true,
      "symbol-sort-key": ["get", "rank"],
    },
  });
  // Hovered (or list-focused) pin: larger. Selected pin: larger with a --ring outline. Layout cannot read
  // feature-state, so these two layers follow the IDs through their filters.
  for (const [id, selected, filterId] of [
    [LAYER.pinActive, false, activeId],
    [LAYER.pinSelected, true, selectedId],
  ] as const) {
    map.addLayer({
      id,
      type: "symbol",
      source: PINS,
      filter: onlyId(filterId),
      layout: {
        "icon-image": pinImage(theme, selected),
        "icon-size": pinSize(ACTIVE_ICON_SCALE),
        "icon-allow-overlap": true,
        "icon-ignore-placement": true,
        "text-field": ["step", ["zoom"], "", LABEL_MIN_ZOOM, ["get", "transformer_id"]],
        "text-font": LABEL_FONT,
        "text-size": LABEL_SIZE_PX,
        "text-offset": [0, LABEL_OFFSET_EM * ACTIVE_ICON_SCALE + 0.4], // clear of the selection ring
        "text-anchor": "top",
        "text-allow-overlap": true,
        "text-ignore-placement": true,
      },
      paint: labelPaint(),
    });
  }
}

function setActive(map: MapLibreMap, id: string | null, active: boolean) {
  if (id === null || !isAlive(map)) return;
  for (const source of [PINS, AREAS]) {
    if (map.getSource(source)) map.setFeatureState({ source, id }, { active });
  }
}

const idOf = (e: MapLayerMouseEvent) => {
  const id = e.features?.[0]?.properties?.transformer_id;
  return typeof id === "string" ? id : null;
};

/** The nearest pin within TAP_TOLERANCE_PX of the tap, else a cluster, else the service area under it. */
function pickAt(map: MapLibreMap, e: MapMouseEvent) {
  const { x, y } = e.point;
  const TAP_TOLERANCE_PX = tapTolerancePx();
  const box: [[number, number], [number, number]] = [
    [x - TAP_TOLERANCE_PX, y - TAP_TOLERANCE_PX],
    [x + TAP_TOLERANCE_PX, y + TAP_TOLERANCE_PX],
  ];
  const nearest = (layer: string) =>
    map
      .queryRenderedFeatures(box, { layers: [layer] })
      .map((feature) => {
        const at =
          feature.geometry.type === "Point" ? map.project(feature.geometry.coordinates as [number, number]) : e.point;
        return { feature, distance: Math.hypot(at.x - x, at.y - y) };
      })
      .sort((a, b) => a.distance - b.distance)[0];
  // Pins win ties: a transformer's own clamps cluster around it, and the pin is the bigger target.
  const pin = nearest(LAYER.pins);
  const clamp = nearest(LAYER.clamps);
  if (clamp !== undefined && (pin === undefined || clamp.distance < pin.distance)) {
    return { kind: "clamp" as const, feature: clamp.feature };
  }
  if (pin !== undefined) return { kind: "pin" as const, feature: pin.feature };
  const charger = nearest(LAYER.chargers);
  if (charger !== undefined) return { kind: "charger" as const, feature: charger.feature };
  const cluster = nearest(LAYER.clusters);
  if (cluster !== undefined) return { kind: "cluster" as const, feature: cluster.feature };
  const area = map.queryRenderedFeatures(e.point, { layers: [LAYER.areaFill, LAYER.coverageFill] })[0];
  return area === undefined ? null : { kind: "pin" as const, feature: area };
}

const reducedMotion = () =>
  typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Moves focus into a popover when it opens (or changes), and closes it on Escape. */
function usePopoverFocus(
  closeRef: RefObject<HTMLButtonElement | null>,
  key: string,
  onClose: () => void,
  takeFocus = true,
) {
  const latestClose = useRef(onClose);
  latestClose.current = onClose;
  useEffect(() => {
    if (takeFocus) closeRef.current?.focus();
  }, [closeRef, key, takeFocus]);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") latestClose.current();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);
}

/** A clamp's device facts. Never its household's identity or usage (RA 10173). */
function ClampPopover({ clamp, asOf, onClose }: { clamp: Clamp; asOf: string | null; onClose: () => void }) {
  const online = clamp.status === "online";
  const closeRef = useRef<HTMLButtonElement>(null);
  usePopoverFocus(closeRef, clamp.clamp_id, onClose);
  return (
    <div
      role="dialog"
      aria-label={`Clamp ${clamp.clamp_id}, ${online ? "online" : "offline"}`}
      className="absolute top-2 right-14 left-2 z-20 grid max-lg:top-24 gap-2 rounded-xl border bg-popover p-4 shadow-lg sm:left-auto sm:w-80"
    >
      <div className="flex items-center gap-2">
        <h2 className="min-w-0 truncate text-xl">{clamp.clamp_id}</h2>
        {/* Neutral on purpose: tier colors mean risk, not device health. Dot shape + word carry status. */}
        <Badge variant="secondary" className="gap-1.5 px-2.5 font-semibold">
          <span
            aria-hidden="true"
            className={cn("size-2 rounded-full", online ? "bg-current" : "border border-current")}
          />
          {online ? "Online" : "Offline"}
        </Badge>
        <Button
          variant="ghost"
          size="icon"
          className="ml-auto size-11 shrink-0 rounded-full sm:size-9"
          aria-label="Close"
          ref={closeRef}
          onClick={onClose}
        >
          <X aria-hidden="true" />
        </Button>
      </div>
      <p className="text-sm">{reportAge(clamp.last_seen_at, asOf)}</p>
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        <dt className="text-muted-foreground">Transformer</dt>
        <dd>{clamp.transformer_id}</dd>
        <dt className="text-muted-foreground">Installed</dt>
        <dd>
          {new Date(clamp.installed_at).toLocaleDateString([], { year: "numeric", month: "short", day: "numeric" })}
        </dd>
        <dt className="text-muted-foreground">Sensor</dt>
        <dd>{clamp.ct_model}</dd>
      </dl>
      <span>
        <SimulatedLabel show={clamp.is_simulated} />
      </span>
    </div>
  );
}

const kw = new Intl.NumberFormat([], { maximumFractionDigits: 1 });

/** A public charger's DOE listing: connectors, power and price where listed. */
export function ChargerPopover({
  charger,
  pinned,
  onClose,
}: {
  charger: Charger;
  /** Opened by a tap or click (focus moves in), not by hover (focus stays put). */
  pinned: boolean;
  onClose: () => void;
}) {
  const closeRef = useRef<HTMLButtonElement>(null);
  usePopoverFocus(closeRef, charger.station_id, onClose, pinned);
  const price = priceRange(charger.price_min_php_kwh, charger.price_max_php_kwh);
  const place = [charger.barangay, charger.city].filter(Boolean).join(", ");
  return (
    <div
      role="dialog"
      aria-label={`EV charger ${charger.name}`}
      className="absolute top-2 right-14 left-2 z-20 grid max-lg:top-24 gap-2 rounded-xl border bg-popover p-4 shadow-lg sm:left-auto sm:w-80"
    >
      <div className="flex items-start gap-2">
        <div className="grid min-w-0 gap-0.5">
          <h2 className="text-xl">{charger.name}</h2>
          {place !== "" && <p className="text-sm text-muted-foreground">{place}</p>}
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="ml-auto size-11 shrink-0 rounded-full sm:size-9"
          aria-label="Close"
          ref={closeRef}
          onClick={onClose}
        >
          <X aria-hidden="true" />
        </Button>
      </div>
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        <dt className="text-muted-foreground">Connectors</dt>
        <dd className="tabular-nums">
          {charger.n_ac ?? "?"} AC, {charger.n_dc ?? "?"} DC
        </dd>
        <dt className="text-muted-foreground">Power</dt>
        <dd className="tabular-nums">
          {charger.max_capacity_kw == null ? "max kW not listed" : `Up to ${kw.format(charger.max_capacity_kw)} kW`}
        </dd>
        {price !== null && (
          <>
            <dt className="text-muted-foreground">Price</dt>
            <dd className="tabular-nums">{price}</dd>
          </>
        )}
      </dl>
      <p className="text-sm text-muted-foreground">Source: DOE</p>
    </div>
  );
}

/** A small card for the tapped pin: ID, tier, top reason and Open. */
function PinPopover({
  item,
  clamps,
  links,
  reachKm,
  onClose,
  onOpen,
}: {
  item: Item;
  clamps: ClampCount | undefined;
  links: Links;
  /** Null until the charger list loads. */
  reachKm: number | null;
  onClose: () => void;
  onOpen: () => void;
}) {
  const closeRef = useRef<HTMLButtonElement>(null);
  // Escape closes it, which also clears the link lines; focus stays where it was.
  usePopoverFocus(closeRef, item.transformer_id, onClose, false);
  return (
    <div
      role="dialog"
      aria-label={`${item.transformer_id}, ${item.risk.tier}`}
      className="absolute top-2 right-14 left-2 z-20 grid max-lg:top-24 gap-2 rounded-xl border bg-popover p-4 shadow-lg sm:left-auto sm:w-80"
    >
      <div className="flex items-center gap-2">
        <h2 className="text-xl">{item.transformer_id}</h2>
        <TierBadge tier={item.risk.tier} />
        {item.action != null && <ActionBadge action={item.action} />}
        <Button
          variant="ghost"
          size="icon"
          className="ml-auto size-11 rounded-full sm:size-9"
          aria-label="Close"
          ref={closeRef}
          onClick={onClose}
        >
          <X aria-hidden="true" />
        </Button>
      </div>
      <p className="text-sm">{item.risk.reasons[0] ?? "No reason given."}</p>
      <p className="flex flex-wrap gap-x-2 text-sm text-muted-foreground">
        <span>Confidence {formatPct(item.risk.confidence)}</span>
        <span aria-hidden="true">·</span>
        <span>Coverage {formatPct(item.risk.coverage_pct)}</span>
        {clamps !== undefined && (
          <>
            <span aria-hidden="true">·</span>
            <span>
              Clamps {clamps.online} of {clamps.total} online
            </span>
          </>
        )}
      </p>
      <p className="text-sm tabular-nums">
        {links.clamps} {links.clamps === 1 ? "clamp" : "clamps"} linked
        {reachKm !== null &&
          ` · ${links.chargers} EV ${links.chargers === 1 ? "charger" : "chargers"} within ${reachKm} km (${links.dc} DC)`}
      </p>
      <Button className="min-h-11 justify-self-start rounded-full sm:min-h-9" onClick={onOpen}>
        Open {item.transformer_id}
      </Button>
    </div>
  );
}

interface TransformerMapProps {
  items: Item[];
  /** IDs the list currently shows (tier filter and ID search); the map draws only these. */
  shownIds: ReadonlySet<string>;
  /** Clamp devices; drawn as dots at street zoom. */
  clamps: Clamp[];
  /** Clamp status could not load: the legend says so and offers Retry. */
  clampsFailed: boolean;
  onRetryClamps: () => void;
  /** The data's own clock for clamp reports (latest report of any clamp). */
  clampsAsOf: string | null;
  clampCounts: Map<string, ClampCount>;
  activeId: string | null;
  /** The pin whose popover is open. */
  selectedId: string | null;
  /** Set by keyboard focus on a list row: the map eases to that pin. */
  focusId: string | null;
  onHover: (id: string | null) => void;
  onSelect: (id: string | null) => void;
  onOpen: (id: string) => void;
  /** Width covered by the list panel on the left, in px. */
  leftInsetPx: number;
  overlay: Overlay;
  /** Null until the API's thresholds load; areas then draw unfilled. */
  coverageBands: CoverageBands | null;
  /** DOE public chargers, drawn on the EV overlay with a ring of `ringRadiusM`. */
  chargers: Charger[];
  ringRadiusM: number;
  /** Legend for the active overlay, drawn over the map's lower right. */
  legend: (zoom: number) => ReactNode;
}

/** Engineer map on an OSM basemap in 3D. The list beside it has the same transformers in words. */
export function TransformerMap({
  items,
  shownIds,
  clamps,
  clampCounts,
  clampsAsOf,
  clampsFailed,
  onRetryClamps,
  activeId,
  selectedId,
  focusId,
  onHover,
  onSelect,
  onOpen,
  leftInsetPx,
  overlay,
  coverageBands,
  chargers,
  ringRadiusM,
  legend,
}: TransformerMapProps) {
  const mapRef = useRef<MapLibreMap | null>(null);
  const geolocateRef = useRef<GeolocateControl | null>(null);
  const bounds = useMemo(() => boundsOf(items), [items]);
  // Read once: the map is created once, and later data should not yank the camera.
  const [start] = useState(() => {
    const first = [...items].sort(byQueue)[0];
    return first === undefined ? undefined : { center: [first.lon, first.lat] as [number, number], zoom: START_ZOOM };
  });
  const selected = items.find((i) => i.transformer_id === selectedId);
  const links = useMemo(
    () => transformerLinks(selected, clamps, chargers, ringRadiusM),
    [selected, clamps, chargers, ringRadiusM],
  );
  const [clampId, setClampId] = useState<string | null>(null);
  // A charger opens on hover (mouse) or tap; a tapped one stays open after the pointer leaves.
  const [charger, setCharger] = useState<{ id: string; pinned: boolean } | null>(null);
  const [zoom, setZoom] = useState(0);
  const [locationMessage, setLocationMessage] = useState("");
  useEffect(() => {
    const geolocate = geolocateRef.current;
    if (geolocate !== null) geolocate.options.fitBoundsOptions = geolocateFitOptions(leftInsetPx);
  }, [leftInsetPx]);
  useEffect(() => {
    const map = mapRef.current;
    if (!isAlive(map) || clampId === null || !map.getSource(CLAMPS)) return;
    map.setFeatureState({ source: CLAMPS, id: clampId }, { selected: true });
    return () => {
      if (isAlive(map) && map.getSource(CLAMPS)) {
        map.setFeatureState({ source: CLAMPS, id: clampId }, { selected: false });
      }
    };
  }, [clampId]);
  const selectedClamp = clamps.find((c) => c.clamp_id === clampId);
  const shownCharger = chargers.find((c) => c.station_id === charger?.id);
  // One popover at a time: picking a transformer closes the clamp and charger popovers.
  useEffect(() => {
    if (selectedId !== null) {
      setClampId(null);
      setCharger(null);
    }
  }, [selectedId]);
  useEffect(() => {
    if (overlay !== "ev") setCharger(null);
  }, [overlay]);
  const latest = useRef({
    items,
    shownIds,
    clamps,
    onHover,
    onSelect,
    setClampId,
    setCharger,
    activeId,
    selectedId,
    clampId,
    leftInsetPx,
    overlay,
    coverageBands,
    chargers,
    ringRadiusM,
    links,
  });
  latest.current = {
    items,
    shownIds,
    clamps,
    onHover,
    onSelect,
    setClampId,
    setCharger,
    activeId,
    selectedId,
    clampId,
    leftInsetPx,
    overlay,
    coverageBands,
    chargers,
    ringRadiusM,
    links,
  };

  useEffect(() => {
    const map = mapRef.current;
    if (isAlive(map)) map.getSource<GeoJSONSource>(LINKS)?.setData(links.geojson);
  }, [links]);

  useEffect(() => {
    const map = mapRef.current;
    if (isAlive(map)) applyOverlay(map, overlay);
  }, [overlay]);

  useEffect(() => {
    const map = mapRef.current;
    if (!isAlive(map)) return;
    map.getSource<GeoJSONSource>(CHARGERS)?.setData(chargersGeoJson(chargers));
    map.getSource<GeoJSONSource>(CHARGER_RINGS)?.setData(ringsGeoJson(chargers, ringRadiusM));
  }, [chargers, ringRadiusM]);

  useEffect(() => {
    const map = mapRef.current;
    if (map === null) return;
    setActive(map, activeId, true);
    return () => setActive(map, activeId, false);
  }, [activeId]);

  useEffect(() => {
    const map = mapRef.current;
    if (!isAlive(map) || !map.getLayer(LAYER.pinLabels)) return;
    map.setFilter(LAYER.pinActive, onlyId(activeId));
    map.setFilter(LAYER.pinSelected, onlyId(selectedId));
    map.setFilter(LAYER.pinLabels, labelFilter(activeId, selectedId));
  }, [activeId, selectedId]);

  useEffect(() => {
    const map = mapRef.current;
    const item = latest.current.items.find((i) => i.transformer_id === focusId);
    if (!isAlive(map) || item === undefined) return;
    map.easeTo({
      center: [item.lon, item.lat],
      zoom: FOCUS_ZOOM,
      duration: reducedMotion() ? 0 : EASE_MS,
      padding: { top: 0, right: 0, bottom: 0, left: leftInsetPx },
    });
  }, [focusId, leftInsetPx]);

  useEffect(() => {
    const map = mapRef.current;
    if (!isAlive(map)) return;
    map.getSource<GeoJSONSource>(PINS)?.setData(shownPins(items, shownIds));
    map.getSource<GeoJSONSource>(AREAS)?.setData(areasGeoJson(items, shownIds, coverageBands));
    map.getSource<GeoJSONSource>(CLAMPS)?.setData(clampsGeoJson(clamps, shownIds));
  }, [items, shownIds, clamps, coverageBands]);

  return (
    <Map
      bounds={bounds}
      start={start}
      cooperativeGestures={false}
      label="Map of transformers by risk tier, with estimated service areas. The list has the same transformers."
      className="h-full rounded-none"
      leftInsetPx={leftInsetPx}
      errorMessage="Map could not load. The list has every transformer."
      onReady={(map) => {
        mapRef.current = map;
        setZoom(map.getZoom());
        map.on("zoomend", () => setZoom(map.getZoom()));
        const geolocate = new GeolocateControl({
          positionOptions: { enableHighAccuracy: true, timeout: 10_000, maximumAge: 5 * 60_000 },
          trackUserLocation: false,
          fitBoundsOptions: geolocateFitOptions(leftInsetPx),
        });
        geolocateRef.current = geolocate;
        geolocate.on("geolocate", (position: { coords: GeolocationCoordinates }) => {
          setLocationMessage("");
          map.flyTo({
            center: [position.coords.longitude, position.coords.latitude],
            zoom: FOCUS_ZOOM,
            duration: reducedMotion() ? 0 : EASE_MS,
            padding: {
              top: MAP_PADDING_PX,
              right: MAP_PADDING_PX,
              bottom: MAP_PADDING_PX,
              left: MAP_PADDING_PX + latest.current.leftInsetPx,
            },
          });
        });
        geolocate.on("error", () => {
          setLocationMessage("Location unavailable. Allow browser location access; local network pages need HTTPS.");
        });
        map.addControl(geolocate, "top-right");
        if (!("geolocation" in navigator)) {
          setLocationMessage("Location is not available in this browser.");
        }
        // One click handler with a tolerance box: a cluster zooms in to split; a pin or area opens its popover.
        map.on("click", async (e) => {
          const picked = pickAt(map, e);
          if (picked === null) {
            latest.current.onSelect(null);
            latest.current.setClampId(null);
            latest.current.setCharger(null);
            return;
          }
          const { feature } = picked;
          if (picked.kind === "charger") {
            const id = feature.properties?.station_id;
            latest.current.onSelect(null);
            latest.current.setClampId(null);
            if (typeof id === "string") latest.current.setCharger({ id, pinned: true });
            return;
          }
          latest.current.setCharger(null);
          if (picked.kind === "clamp") {
            const id = feature.properties?.clamp_id;
            latest.current.onSelect(null);
            if (typeof id === "string") latest.current.setClampId(id);
            return;
          }
          if (picked.kind === "cluster") {
            const clusterId = feature.properties?.cluster_id;
            if (typeof clusterId !== "number" || feature.geometry.type !== "Point") return;
            const zoom = await map.getSource<GeoJSONSource>(PINS)?.getClusterExpansionZoom(clusterId);
            map.easeTo({
              center: feature.geometry.coordinates as [number, number],
              zoom,
              duration: reducedMotion() ? 0 : EASE_MS,
            });
            return;
          }
          const id = feature.properties?.transformer_id;
          if (typeof id === "string") latest.current.onSelect(id);
        });
        for (const layer of [LAYER.pins, LAYER.areaFill, LAYER.coverageFill]) {
          map.on("mousemove", layer, (e) => {
            map.getCanvas().style.cursor = "pointer";
            latest.current.onHover(idOf(e));
          });
          map.on("mouseleave", layer, () => {
            map.getCanvas().style.cursor = "";
            latest.current.onHover(null);
          });
        }
        for (const layer of [LAYER.clusters, LAYER.clamps]) {
          map.on("mouseenter", layer, () => (map.getCanvas().style.cursor = "pointer"));
          map.on("mouseleave", layer, () => (map.getCanvas().style.cursor = ""));
        }
        map.on("mousemove", LAYER.chargers, (e) => {
          map.getCanvas().style.cursor = "pointer";
          const id = e.features?.[0]?.properties?.station_id;
          if (typeof id === "string" && latest.current.selectedId === null) {
            latest.current.setCharger((now) => (now?.pinned ? now : { id, pinned: false }));
          }
        });
        map.on("mouseleave", LAYER.chargers, () => {
          map.getCanvas().style.cursor = "";
          latest.current.setCharger((now) => (now?.pinned ? now : null));
        });
      }}
      onStyle={(map) => {
        const now = latest.current;
        const theme = themeNow();
        const style = map.style;
        // Images are drawn from the tokens of the theme that just loaded; symbols redraw once they land.
        registerPinImages(map, theme, tokenColors(), window.devicePixelRatio || 1, undefined, () => {
          return isAlive(map) && map.style === style;
        }).catch((error: unknown) => console.warn("Map pin icons failed to draw", error));
        addLayers(
          map,
          now.items,
          now.shownIds,
          now.clamps,
          now.coverageBands,
          now.chargers,
          now.ringRadiusM,
          theme,
          now.activeId,
          now.selectedId,
          now.links,
        );
        applyOverlay(map, now.overlay);
        setActive(map, now.activeId, true);
        const selectedClampId = latest.current.clampId;
        if (selectedClampId !== null) map.setFeatureState({ source: CLAMPS, id: selectedClampId }, { selected: true });
      }}
    >
      <Button
        variant="outline"
        className="absolute bottom-10 z-10 min-h-11 rounded-full bg-card shadow-lg max-lg:bottom-20 sm:min-h-9"
        style={{ left: leftInsetPx + 8 }}
        onClick={() => {
          setClampId(null);
          onSelect(null);
          const map = mapRef.current;
          if (isAlive(map))
            map.fitBounds(bounds, { ...fitOptions(leftInsetPx), duration: reducedMotion() ? 0 : EASE_MS });
        }}
      >
        <Maximize2 aria-hidden="true" />
        See all {items.length}
      </Button>
      {locationMessage !== "" && (
        <p
          role="status"
          className="absolute right-2 bottom-36 z-10 max-w-72 rounded-lg border bg-card/95 px-3 py-2 text-sm text-muted-foreground shadow-lg max-lg:bottom-44"
        >
          {locationMessage}
        </p>
      )}
      <div className="pointer-events-none absolute right-2 bottom-10 grid justify-items-end gap-1 max-lg:bottom-20">
        {legend(zoom)}
        {clampsFailed && (
          <p
            role="status"
            className="pointer-events-auto flex items-center gap-2 rounded-full bg-card/95 py-0.5 pr-1 pl-2.5 text-xs text-muted-foreground"
          >
            Clamp status unavailable
            <Button variant="outline" className="h-7 rounded-full px-3 text-xs" onClick={onRetryClamps}>
              Retry
            </Button>
          </p>
        )}
        {selected !== undefined && (
          <p className="flex flex-wrap items-center gap-x-2 rounded-xl bg-card/90 px-2.5 py-0.5 text-xs text-muted-foreground">
            <span aria-hidden="true" className="w-4 border-t-2 border-brand" />
            Lines: its clamps (dashed = offline)
            <span aria-hidden="true">·</span>
            <span aria-hidden="true" className="w-4 border-t-2 border-dotted border-foreground" />
            EV chargers within {ringRadiusM > 0 ? `${ringRadiusM / 1000} km` : "reach"}
          </p>
        )}
        {clamps.length > 0 && (
          <p className="flex items-center gap-2 rounded-full bg-card/90 px-2.5 py-0.5 text-xs text-muted-foreground">
            <span aria-hidden="true" className="size-2 rounded-full bg-muted-foreground" /> Clamp online
            <span aria-hidden="true" className="size-2 rounded-full border border-muted-foreground" /> Offline
            {zoom < CLAMP_MIN_ZOOM && <span>(zoom in)</span>}
          </p>
        )}
      </div>
      {selected !== undefined && (
        <PinPopover
          item={selected}
          clamps={clampCounts.get(selected.transformer_id)}
          links={links}
          reachKm={ringRadiusM > 0 ? ringRadiusM / 1000 : null}
          onClose={() => onSelect(null)}
          onOpen={() => onOpen(selected.transformer_id)}
        />
      )}
      {selectedClamp !== undefined && (
        <ClampPopover clamp={selectedClamp} asOf={clampsAsOf} onClose={() => setClampId(null)} />
      )}
      {shownCharger !== undefined && selected === undefined && selectedClamp === undefined && (
        <ChargerPopover charger={shownCharger} pinned={charger?.pinned ?? false} onClose={() => setCharger(null)} />
      )}
    </Map>
  );
}
