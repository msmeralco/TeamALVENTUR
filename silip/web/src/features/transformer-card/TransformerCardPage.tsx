import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { api, unwrap } from "../../shared/api/client";
import { QueryView, SimulatedLabel, TierBadge } from "../../shared/ui";

/** One transformer: tier, all reasons, and peak load in the last 48 h vs the next 24 h. */
export function TransformerCardPage() {
  const { transformerId = "" } = useParams();
  const query = useQuery({
    queryKey: ["transformer", transformerId],
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/transformers/{transformer_id}", { params: { path: { transformer_id: transformerId } } }),
      ),
  });
  return (
    <section>
      <QueryView {...query} isEmpty={() => false} emptyMessage="" onRetry={() => void query.refetch()}>
        {(card) => {
          const peak = (forecast: boolean) =>
            Math.max(...card.load.filter((p) => p.is_forecast === forecast).map((p) => p.load_pct));
          return (
            <>
              <h1>
                {card.transformer_id} <TierBadge tier={card.risk.tier} />
              </h1>
              <SimulatedLabel show={card.is_simulated} />
              <ul>
                {card.risk.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
              <p>
                Peak load last 48 h: {Math.round(peak(false) * 100)}% · next 24 h (forecast):{" "}
                {Math.round(peak(true) * 100)}% of {card.rated_kva} kVA
              </p>
              <p className="muted">
                Confidence {Math.round(card.risk.confidence * 100)}%. Decision support only; an engineer decides.
              </p>
            </>
          );
        }}
      </QueryView>
    </section>
  );
}
