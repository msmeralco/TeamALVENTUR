import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "../../shared/api/client";
import { QueryView, SimulatedLabel, formatMinutes } from "../../shared/ui";

/** Public outage view: area, cause and a restoration range. No household data. */
export function OutagesPage() {
  const query = useQuery({
    queryKey: ["outages", "open"],
    queryFn: async () => unwrap(await api.GET("/api/v1/outages", { params: { query: { status: "open" } } })),
  });
  return (
    <section>
      <h1>Power outages</h1>
      <QueryView
        {...query}
        isEmpty={(outages) => outages.length === 0}
        emptyMessage="No open outages right now."
        onRetry={() => void query.refetch()}
      >
        {(outages) => (
          <>
            <SimulatedLabel show={outages.some((o) => o.is_simulated)} />
            <ul className="list">
              {outages.map((o) => (
                <li key={o.outage_id}>
                  <strong>Cause: {o.cause}</strong>
                  <div>
                    Estimated restoration: {formatMinutes(o.eta_p10_min)} to {formatMinutes(o.eta_p90_min)} after{" "}
                    {new Date(o.started_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </div>
                  <div className="muted">
                    Area near {o.area_lat}, {o.area_lon}
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
