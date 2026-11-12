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
import { Map, cssVar, fitOptions, isAlive } from "../../shared/ui/components/map";
import { AREA_MIN_ZOOM, RING_MIN_ZOOM, coverageBand, type CoverageBands, type Overlay } from "./overlays";
import { serviceAreas } from "./serviceAreas";

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
const LAYER = {
  areaFill: "service-area-fill",
  areaVolume: "service-area-volume",
  areaOutline: "service-area-outline",
  clusters: "transformer-clusters",
  clusterCount: "transformer-cluster-count",
  pins: "transformer-pins",
  pinLabels: "transformer-pin-labels",
  clamps: "clamp-points",
  coverageFill: "coverage-fill",
  coverageOutline: "coverage-outline",
  chargers: "ev-charger-points",
  chargerRings: "ev-charger-rings",
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
const PIN_RADIUS_PX = { Critical: 7, Watch: 6, OK: 5 } as const;
const ACTIVE_SCALE = 1.6;
const CLAMP_MIN_ZOOM = 15; // single homes are only readable at street level
// Opens at street level on the most urgent transformer, so 3D buildings (14+) and clamps (15+) show at once.
const START_ZOOM = 15.5;
const CLAMP_RADIUS_PX = 2.5;
const CLAMP_SELECTED_RADIUS_PX = 5;
// Pins are small; a tap within this many px of one picks it (about a 32 px target around the pin).
const TAP_TOLERANCE_PX = 16;
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
      properties: { station_id: c.station_id },
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
    type: "circle",
    source: CHARGERS,
    layout: { visibility: "none" },
    // Hollow and larger than a pin, so a charger never reads as a transformer.
    paint: {
      "circle-color": cssVar("--card"),
      "circle-radius": 6,
      "circle-stroke-color": cssVar("--foreground"),
      "circle-stroke-width": 3,
    },
  });
  map.addLayer({
    id: LAYER.clusters,
    type: "circle",
    source: PINS,
    filter: ["has", "point_count"],
    paint: {
      "circle-color": cssVar("--card"),
      "circle-stroke-color": clusterColor,
      "circle-stroke-width": 4,
      "circle-radius": ["step", ["get", "point_count"], 16, 5, 20, 15, 26],
    },
  });
  map.addLayer({
    id: LAYER.clusterCount,
    type: "symbol",
    source: PINS,
    filter: ["has", "point_count"],
    layout: { "text-field": ["get", "point_count_abbreviated"], "text-font": LABEL_FONT, "text-size": 13 },
    paint: { "text-color": cssVar("--foreground") },
  });
  const radius: ExpressionSpecification = [
    "match",
    ["get", "tier"],
    "Critical",
    PIN_RADIUS_PX.Critical,
    "Watch",
    PIN_RADIUS_PX.Watch,
    PIN_RADIUS_PX.OK,
  ];
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
  map.addLayer({
    id: LAYER.pins,
    type: "circle",
    source: PINS,
    filter: ["!", ["has", "point_count"]],
    layout: { "circle-sort-key": ["get", "rank"] },
    paint: {
      "circle-color": tier,
      "circle-radius": ["case", isActive, ["*", radius, ACTIVE_SCALE], radius],
      "circle-stroke-color": cssVar("--card"),
      "circle-stroke-width": 2,
    },
  });
  map.addLayer({
    id: LAYER.pinLabels,
    type: "symbol",
    source: PINS,
    minzoom: LABEL_MIN_ZOOM,
    filter: ["!", ["has", "point_count"]],
    layout: {
      "text-field": ["get", "transformer_id"],
      "text-font": LABEL_FONT,
      "text-size": 12,
      "text-offset": [0, 1.2],
      "text-anchor": "top",
    },
    paint: { "text-color": cssVar("--foreground"), "text-halo-color": cssVar("--card"), "text-halo-width": 1.5 },
  });
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
  const cluster = nearest(LAYER.clusters);
  if (cluster !== undefined) return { kind: "cluster" as const, feature: cluster.feature };
  const area = map.queryRenderedFeatures(e.point, { layers: [LAYER.areaFill, LAYER.coverageFill] })[0];
  return area === undefined ? null : { kind: "pin" as const, feature: area };
}

const reducedMotion = () =>
  typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Moves focus into a popover when it opens (or changes), and closes it on Escape. */
function usePopoverFocus(closeRef: RefObject<HTMLButtonElement | null>, key: string, onClose: () => void) {
  const latestClose = useRef(onClose);
  latestClose.current = onClose;
  useEffect(() => {
    closeRef.current?.focus();
  }, [closeRef, key]);
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

/** A small card for the tapped pin: ID, tier, top reason and Open. */
function PinPopover({
  item,
  clamps,
  onClose,
  onOpen,
}: {
  item: Item;
  clamps: ClampCount | undefined;
  onClose: () => void;
  onOpen: () => void;
}) {
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
  const [clampId, setClampId] = useState<string | null>(null);
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
  // One popover at a time: picking a transformer closes the clamp popover.
  useEffect(() => {
    if (selectedId !== null) setClampId(null);
  }, [selectedId]);
  const latest = useRef({
    items,
    shownIds,
    clamps,
    onHover,
    onSelect,
    setClampId,
    activeId,
    clampId,
    leftInsetPx,
    overlay,
    coverageBands,
    chargers,
    ringRadiusM,
  });
  latest.current = {
    items,
    shownIds,
    clamps,
    onHover,
    onSelect,
    setClampId,
    activeId,
    clampId,
    leftInsetPx,
    overlay,
    coverageBands,
    chargers,
    ringRadiusM,
  };

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
            return;
          }
          const { feature } = picked;
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
      }}
      onStyle={(map) => {
        const now = latest.current;
        addLayers(map, now.items, now.shownIds, now.clamps, now.coverageBands, now.chargers, now.ringRadiusM);
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
          onClose={() => onSelect(null)}
          onOpen={() => onOpen(selected.transformer_id)}
        />
      )}
      {selectedClamp !== undefined && (
        <ClampPopover clamp={selectedClamp} asOf={clampsAsOf} onClose={() => setClampId(null)} />
      )}
    </Map>
  );
}
