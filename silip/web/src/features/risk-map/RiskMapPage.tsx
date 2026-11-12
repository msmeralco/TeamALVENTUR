import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, unwrap, type Schemas } from "../../shared/api/client";
import { QueryView, SimulatedLabel, TierBadge } from "../../shared/ui";

const PIN_COLOR = { OK: "var(--ok)", Watch: "var(--watch)", Critical: "var(--critical)" } as const;

/** Pins placed by lat/lon in a plain SVG. A basemap (MapLibre) can replace this later. */
function PinPlot({ items }: { items: Schemas["TransformerRisk"][] }) {
  const lats = items.map((i) => i.lat);
  const lons = items.map((i) => i.lon);
  const [minLat, maxLat, minLon, maxLon] = [Math.min(...lats), Math.max(...lats), Math.min(...lons), Math.max(...lons)];
  const x = (lon: number) => 5 + (90 * (lon - minLon)) / (maxLon - minLon || 1);
  const y = (lat: number) => 5 + (90 * (maxLat - lat)) / (maxLat - minLat || 1);
  return (
    <svg
      viewBox="0 0 100 100"
      role="img"
      aria-label="Transformer pins by risk"
      style={{ width: "100%", maxWidth: 480 }}
    >
      {items.map((i) => (
        <circle
          key={i.transformer_id}
          cx={x(i.lon)}
          cy={y(i.lat)}
          r={i.risk.tier === "Critical" ? 2.2 : 1.4}
          fill={PIN_COLOR[i.risk.tier]}
        >
          <title>
            {i.transformer_id}: {i.risk.tier}
          </title>
        </circle>
      ))}
    </svg>
  );
}

/** Engineer risk map: Critical transformers first, each with its top reason and confidence. */
export function RiskMapPage() {
  const query = useQuery({
    queryKey: ["transformers"],
    queryFn: async () => unwrap(await api.GET("/api/v1/transformers")),
  });
  return (
    <section>
      <h1>Transformer risk, next 24 h</h1>
      <QueryView
        {...query}
        isEmpty={(items) => items.length === 0}
        emptyMessage="No transformers in this area."
        onRetry={() => void query.refetch()}
      >
        {(items) => (
          <>
            <SimulatedLabel show={items.some((i) => i.is_simulated)} />
            <PinPlot items={items} />
            <ul className="list">
              {items.map((i) => (
                <li key={i.transformer_id}>
                  <TierBadge tier={i.risk.tier} />{" "}
                  <Link to={`/engineer/transformers/${i.transformer_id}`}>{i.transformer_id}</Link>
                  <div>{i.risk.reasons[0]}</div>
                  <div className="muted">
                    Confidence {Math.round(i.risk.confidence * 100)}% · coverage {Math.round(i.risk.coverage_pct * 100)}
                    % of homes
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </QueryView>
    </section>
  );
}
