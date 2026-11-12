import type { FeatureCollection, Point } from "geojson";
import type { GeoJSONSource, LngLatBoundsLike, Map as MapLibreMap } from "maplibre-gl";
import { useEffect, useMemo, useRef, useState } from "react";
import { Map, cssVar, fitOptions } from "../../shared/ui/components/map";
import { Card } from "../../shared/ui/components/card";

interface Transformer {
  transformer_id: string;
  lat: number;
  lon: number;
}

interface InstallationMapProps {
  lat: number | null;
  lon: number | null;
  locationLabel: string;
  transformer: Transformer | null;
}

type Pin = { kind: "house" | "transformer"; label: string; marker: "H" | "T" };

const SOURCE_ID = "device-installation-pins";

function pins(
  lat: number | null,
  lon: number | null,
  locationLabel: string,
  transformer: Transformer,
): FeatureCollection<Point, Pin> {
  const features: FeatureCollection<Point, Pin>["features"] = [
    {
      type: "Feature",
      geometry: { type: "Point", coordinates: [transformer.lon, transformer.lat] },
      properties: { kind: "transformer", label: `Transformer ${transformer.transformer_id}`, marker: "T" },
    },
  ];
  if (lat !== null && lon !== null && Number.isFinite(lat) && Number.isFinite(lon)) {
    features.push({
      type: "Feature",
      geometry: { type: "Point", coordinates: [lon, lat] },
      properties: { kind: "house", label: locationLabel.trim() || "House location", marker: "H" },
    });
  }
  return { type: "FeatureCollection", features };
}

function boundsFor(lat: number | null, lon: number | null, transformer: Transformer): LngLatBoundsLike {
  const coordinates: [number, number][] = [[transformer.lon, transformer.lat]];
  if (lat !== null && lon !== null && Number.isFinite(lat) && Number.isFinite(lon)) {
    coordinates.push([lon, lat]);
  }
  let west = Math.min(...coordinates.map(([x]) => x));
  let east = Math.max(...coordinates.map(([x]) => x));
  let south = Math.min(...coordinates.map(([, y]) => y));
  let north = Math.max(...coordinates.map(([, y]) => y));
  if (west === east) {
    west -= 0.002;
    east += 0.002;
  }
  if (south === north) {
    south -= 0.002;
    north += 0.002;
  }
  return [
    [west, south],
    [east, north],
  ];
}

export function InstallationMap({ lat, lon, locationLabel, transformer }: InstallationMapProps) {
  const mapRef = useRef<MapLibreMap | null>(null);
  const [styleReady, setStyleReady] = useState(false);
  const [mapReady, setMapReady] = useState(false);
  const data = useMemo(
    () => (transformer ? pins(lat, lon, locationLabel, transformer) : null),
    [lat, lon, locationLabel, transformer],
  );
  const bounds = useMemo(
    () =>
      transformer
        ? boundsFor(lat, lon, transformer)
        : ([
            [-180, -85],
            [180, 85],
          ] as LngLatBoundsLike),
    [lat, lon, transformer],
  );

  function onStyle(map: MapLibreMap) {
    if (!map.getSource(SOURCE_ID)) {
      map.addSource(SOURCE_ID, { type: "geojson", data: data ?? { type: "FeatureCollection", features: [] } });
      map.addLayer({
        id: "house-and-transformer-pins",
        type: "circle",
        source: SOURCE_ID,
        paint: {
          "circle-radius": 10,
          "circle-color": ["match", ["get", "kind"], "house", cssVar("--primary"), cssVar("--watch")],
          "circle-stroke-color": cssVar("--background"),
          "circle-stroke-width": 2,
        },
      });
      map.addLayer({
        id: "house-and-transformer-labels",
        type: "symbol",
        source: SOURCE_ID,
        layout: {
          "text-field": ["get", "marker"],
          "text-size": 11,
          "text-font": ["Noto Sans Bold"],
          "text-allow-overlap": true,
        },
        paint: {
          "text-color": ["match", ["get", "kind"], "house", cssVar("--primary-foreground"), cssVar("--foreground")],
        },
      });
    }
    setStyleReady(true);
  }

  useEffect(() => {
    if (!styleReady || !mapReady || !transformer || !mapRef.current?.getSource(SOURCE_ID)) return;
    (mapRef.current.getSource(SOURCE_ID) as GeoJSONSource).setData(data ?? { type: "FeatureCollection", features: [] });
    mapRef.current.fitBounds(bounds, { ...fitOptions(), duration: 0 });
  }, [bounds, data, mapReady, styleReady, transformer]);

  if (!transformer) return null;
  return (
    <Card className="overflow-hidden p-0 shadow-none">
      <Map
        bounds={bounds}
        label={`House and serving transformer locations for ${transformer.transformer_id}`}
        errorMessage="The map could not load. The coordinates and transformer assignment remain available above."
        className="h-64 rounded-none sm:h-72"
        onReady={(map) => {
          mapRef.current = map;
          setMapReady(true);
        }}
        onStyle={onStyle}
      />
      <div className="flex flex-wrap gap-x-5 gap-y-2 px-4 py-3 text-sm" aria-label="Map legend">
        <span>
          <span
            aria-hidden="true"
            className="mr-2 inline-grid size-5 place-items-center rounded-full bg-primary text-xs text-primary-foreground"
          >
            H
          </span>
          {locationLabel.trim() || "House location"}
        </span>
        <span>
          <span
            aria-hidden="true"
            className="mr-2 inline-grid size-5 place-items-center rounded-full bg-watch text-xs text-background"
          >
            T
          </span>
          Serving transformer {transformer.transformer_id}
        </span>
      </div>
      {lat === null || lon === null ? (
        <p className="px-4 pb-3 text-xs text-muted-foreground">
          The transformer pin is shown. Add house coordinates to place the house pin.
        </p>
      ) : null}
    </Card>
  );
}
