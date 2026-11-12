import type { Schemas } from "../../shared/api/client";
import type { TransformerItem } from "../../shared/risk";
import { HeatIndexChart, type PeakMark } from "../../shared/ui/HeatIndexChart";
import { QueryView, SimulatedLabel } from "../../shared/ui";
import { Card } from "../../shared/ui/components/card";
import { Skeleton } from "../../shared/ui/components/skeleton";
import { formatStamp, WeatherBadge } from "./SummaryRow";
import { useOutlook } from "./queries";

type Outlook = Schemas["AreaOutlook"];

/** Freshness in words, so stale or missing weather is never just a color. */
export function outlookStatusText(outlook: Pick<Outlook, "status" | "issued_at">): string {
  const issued = outlook.issued_at === null ? null : formatStamp(outlook.issued_at);
  if (outlook.status === "missing") return "No weather forecast is available.";
  if (outlook.status === "stale") {
    return issued === null ? "The weather forecast is stale." : `The weather forecast is stale. Last issued ${issued}.`;
  }
  return issued === null ? "Forecast is current." : `Forecast issued ${issued}.`;
}

/** Each queued Critical transformer's forecast peak, for marking on the heat-index line. */
export function criticalPeaks(items: TransformerItem[]): PeakMark[] {
  return items
    .filter((i) => i.risk.tier === "Critical" && i.peak_ts != null)
    .map((i) => ({ ts: i.peak_ts as string, ids: [i.transformer_id] }));
}

/** 48 h heat index across the transformers in view, with the Critical peaks marked on it. */
export function WeatherStrip({ items }: { items: TransformerItem[] }) {
  const query = useOutlook();
  return (
    <section aria-labelledby="weather-title" className="px-4 py-6 sm:px-6">
      <Card className="gap-4 px-6 py-5 shadow-none">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <h2 id="weather-title" className="text-xl">
            Heat index, next 48 h
          </h2>
          {query.data !== undefined && (
            <>
              <WeatherBadge status={query.data.status} />
              <span className="text-sm text-muted-foreground">Source: {query.data.source}</span>
              <SimulatedLabel show={query.data.is_simulated} />
            </>
          )}
        </div>
        <QueryView
          {...query}
          isEmpty={() => false}
          emptyMessage=""
          onRetry={query.refetch}
          skeleton={<Skeleton className="h-36 rounded-xl" />}
        >
          {(outlook) => (
            <div className="grid gap-3">
              <p className="text-sm">{outlookStatusText(outlook)}</p>
              {outlook.hours.length === 0 ? (
                <p className="text-sm text-muted-foreground">No forecast hours to show.</p>
              ) : (
                <HeatIndexChart
                  hours={outlook.hours.map((h) => ({
                    ts: h.ts,
                    heatC: h.heat_index_max_c,
                    rainMm: h.precipitation_max_mm,
                  }))}
                  marks={criticalPeaks(items)}
                />
              )}
              <p className="text-sm text-muted-foreground">Hottest hour across the weather cells in view.</p>
            </div>
          )}
        </QueryView>
      </Card>
    </section>
  );
}
