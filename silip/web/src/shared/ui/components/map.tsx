import maplibregl, { type FitBoundsOptions, type LngLatBoundsLike, type Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { cn } from "../cn";

// OpenFreeMap: free OpenStreetMap vector tiles, no API key. Attribution comes with the style.
const STYLE_URL = {
  light: "https://tiles.openfreemap.org/styles/positron",
  dark: "https://tiles.openfreemap.org/styles/dark",
} as const;
const BUILDINGS_LAYER_ID = "buildings-3d";
const BUILDINGS_MIN_ZOOM = 14;
const DEFAULT_PITCH_DEG = 50;
const DEFAULT_BEARING_DEG = -12;
const FIT_PADDING_PX = 48;
const FIT_MAX_ZOOM = 16; // one transformer, or all at one point, would otherwise zoom to the max
const SMALL_SCREEN = "(max-width: 40rem)"; // Tailwind `sm`

/** Fit options shared by the first view and any "see all" action, keeping pins clear of a left panel. */
export function fitOptions(leftInsetPx = 0): FitBoundsOptions {
  return {
    padding: { top: FIT_PADDING_PX, right: FIT_PADDING_PX, bottom: FIT_PADDING_PX, left: FIT_PADDING_PX + leftInsetPx },
    maxZoom: FIT_MAX_ZOOM,
    pitch: DEFAULT_PITCH_DEG,
    bearing: DEFAULT_BEARING_DEG,
  };
}

/**
 * False once `map.remove()` has run (unmount, hot reload): MapLibre drops its style then and most calls
 * throw. Effects and clean-ups that outlive the map check this first.
 */
export function isAlive(map: MapLibreMap | null): map is MapLibreMap {
  return map !== null && (map.style as unknown) !== undefined;
}

/** Reads a design token, so map paint follows the same colors as the rest of the UI. */
export function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

/** The theme the map follows: the theme menu's choice on <html>, else the system setting. */
export function prefersDark(): boolean {
  const theme = document.documentElement.dataset.theme;
  if (theme === "dark") return true;
  if (theme === "light") return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

/** Extruded buildings from the OpenMapTiles `building` layer (heights in metres). */
function addBuildings(map: MapLibreMap) {
  if (map.getLayer(BUILDINGS_LAYER_ID)) return;
  map.addLayer({
    id: BUILDINGS_LAYER_ID,
    type: "fill-extrusion",
    source: "openmaptiles",
    "source-layer": "building",
    minzoom: BUILDINGS_MIN_ZOOM,
    paint: {
      "fill-extrusion-color": cssVar("--map-building"),
      "fill-extrusion-height": ["coalesce", ["get", "render_height"], 0],
      "fill-extrusion-base": ["coalesce", ["get", "render_min_height"], 0],
      "fill-extrusion-opacity": 0.85,
    },
  });
}

interface MapProps {
  bounds: LngLatBoundsLike;
  className?: string;
  label: string;
  /** Once, after the map is created: register event handlers here. */
  onReady?: (map: MapLibreMap) => void;
  /** After every style load (first load and each light/dark switch): add sources and layers here. */
  onStyle?: (map: MapLibreMap) => void;
  /** Shown if the basemap cannot load. */
  errorMessage: string;
  /** Pixels covered on the left by a panel over the map; the first view keeps pins clear of it. */
  leftInsetPx?: number;
  /** Open at this point and zoom instead of fitting `bounds` (e.g. street level, where 3D shows). */
  start?: { center: [number, number]; zoom: number };
  /**
   * Ctrl + scroll to zoom and two fingers to pan, so a page can scroll past an embedded map.
   * Turn off for a full-screen map, where the wheel should just zoom.
   */
  cooperativeGestures?: boolean;
  /** Overlay content, such as a legend. */
  children?: ReactNode;
}

/** A pitched MapLibre map with 3D buildings that follows the light/dark theme. */
export function Map({
  bounds,
  className,
  label,
  onReady,
  onStyle,
  errorMessage,
  leftInsetPx = 0,
  start,
  cooperativeGestures = true,
  children,
}: MapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);
  const callbacks = useRef({ onReady, onStyle });
  callbacks.current = { onReady, onStyle };

  useEffect(() => {
    const container = containerRef.current;
    if (container === null) return;
    let dark = prefersDark();
    const map = new maplibregl.Map({
      container,
      style: STYLE_URL[dark ? "dark" : "light"],
      ...(start === undefined
        ? { bounds, fitBoundsOptions: fitOptions(leftInsetPx) }
        : { center: start.center, zoom: start.zoom, pitch: DEFAULT_PITCH_DEG, bearing: DEFAULT_BEARING_DEG }),
      attributionControl: { compact: true },
      cooperativeGestures,
    });
    // Keep the starting point clear of a panel on the left.
    if (start !== undefined && leftInsetPx > 0) {
      map.jumpTo({ center: start.center, padding: { top: 0, right: 0, bottom: 0, left: leftInsetPx } });
    }
    // Basemap failures (offline, tile server down) leave a blank canvas; say so instead.
    map.on("error", (event) => {
      if (!map.isStyleLoaded()) {
        console.warn("Map style failed to load", event.error);
        setFailed(true);
      }
    });
    map.on("style.load", () => setFailed(false));
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
    map.once("load", () => {
      // On phones, fold the attribution to its (i) button so it does not cover the map.
      if (window.matchMedia(SMALL_SCREEN).matches) {
        container.querySelector(".maplibregl-compact-show")?.classList.remove("maplibregl-compact-show");
      }
    });
    // The container can change size after mount (layout, Suspense, rotation); keep the canvas matched.
    const resizeObserver = new ResizeObserver(() => map.resize());
    resizeObserver.observe(container);
    map.on("style.load", () => {
      addBuildings(map);
      callbacks.current.onStyle?.(map);
    });
    callbacks.current.onReady?.(map);

    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onSchemeChange = () => {
      if (prefersDark() === dark) return;
      dark = !dark;
      map.setStyle(STYLE_URL[dark ? "dark" : "light"]);
    };
    media.addEventListener("change", onSchemeChange);
    // The theme menu sets data-theme on <html>; follow it too.
    const themeObserver = new MutationObserver(onSchemeChange);
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => {
      themeObserver.disconnect();
      media.removeEventListener("change", onSchemeChange);
      resizeObserver.disconnect();
      map.remove();
    };
    // Created once on purpose: `bounds` only sets the first view, and callbacks are read through a ref.
  }, []);

  return (
    <div role="region" aria-label={label} className={cn("relative overflow-hidden rounded-xl bg-muted", className)}>
      <div ref={containerRef} className="h-full w-full" />
      {failed && (
        <p
          role="status"
          className="absolute inset-0 grid place-items-center p-6 text-center text-sm text-muted-foreground"
        >
          {errorMessage}
        </p>
      )}
      {children}
    </div>
  );
}
