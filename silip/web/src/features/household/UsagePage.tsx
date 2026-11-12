import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "../../shared/api/client";
import { QueryView, SimulatedLabel } from "../../shared/ui";

/** The signed-in household's own last 7 days, as daily kWh. */
export function UsagePage() {
  const query = useQuery({
    queryKey: ["me", "usage"],
    queryFn: async () => unwrap(await api.GET("/api/v1/me/usage")),
  });
  return (
    <section>
      <h1>Your usage, last 7 days</h1>
      <QueryView
        {...query}
        isEmpty={(usage) => usage.points.length === 0}
        emptyMessage="No readings from your clamp yet."
        onRetry={() => void query.refetch()}
      >
        {(usage) => {
          const daily = new Map<string, number>();
          for (const point of usage.points) {
            const day = new Date(point.ts).toLocaleDateString();
            daily.set(day, (daily.get(day) ?? 0) + point.kw * 0.25);
          }
          return (
            <>
              <SimulatedLabel show={usage.is_simulated} />
              <p>
                <strong>{usage.total_kwh} kWh</strong> in total
              </p>
              <ul className="list">
                {[...daily].map(([day, kwh]) => (
                  <li key={day}>
                    {day}: {kwh.toFixed(1)} kWh
                  </li>
                ))}
              </ul>
            </>
          );
        }}
      </QueryView>
    </section>
  );
}
