import type { ReactNode } from "react";
import type { Schemas } from "../../shared/api/client";
import { SimulatedLabel, cn } from "../../shared/ui";
import { Badge } from "../../shared/ui/components/badge";
import { Button } from "../../shared/ui/components/button";
import { Skeleton } from "../../shared/ui/components/skeleton";
import { useOutlook, useSummary } from "./queries";
import { HeatChip } from "./WeatherStrip";

type WeatherStatus = Schemas["WeatherSummary"]["status"];

/** "26 May, 11:45 PM": the data runs on its own clock, so the date matters. */
export function formatStamp(iso: string): string {
  return new Date(iso).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

/** Weather freshness as color plus word. Fresh stays neutral; stale and missing take the Watch color. */
export function WeatherBadge({ status }: { status: WeatherStatus }) {
  return (
    <Badge
      variant={status === "fresh" ? "secondary" : undefined}
      className={cn("gap-1.5 px-2.5 font-semibold", status !== "fresh" && "bg-watch-soft text-watch")}
    >
      <span
        aria-hidden="true"
        className={cn("size-2 rounded-full", status === "fresh" ? "bg-current" : "border border-current")}
      />
      Weather {status}
    </Badge>
  );
}

const plainName = (name: string | null) => (name === null ? null : name.replaceAll("_", " "));

function Meta({ label, children }: { label: string; children: ReactNode }) {
  return (
    <span className="text-sm whitespace-nowrap">
      <span className="text-muted-foreground">{label}</span> {children}
    </span>
  );
}

/** Page title and the facts behind every number below it: data time, scoring time, weather and model. */
export function SummaryRow() {
  const query = useSummary();
  const summary = query.data;
  const outlook = useOutlook();
  return (
    <header className="grid gap-2 border-b bg-card px-4 py-3 sm:px-6">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <h1 className="text-3xl tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">Which transformers need action in the next 24 to 48 h, and why.</p>
      </div>
      {summary !== undefined ? (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <SimulatedLabel show={summary.is_simulated} />
          <Meta label="Data as of">{formatStamp(summary.as_of)}</Meta>
          <Meta label="Scored">{formatStamp(summary.scored_at)}</Meta>
          <span className="flex flex-wrap items-center gap-2 text-sm">
            <WeatherBadge status={summary.weather.status} />
            <HeatChip outlook={outlook.data} />
            <span className="text-muted-foreground">
              {summary.weather.issued_at === null
                ? "No forecast issued."
                : `Issued ${formatStamp(summary.weather.issued_at)}.`}{" "}
              Source: {summary.weather.source}
            </span>
          </span>
          <Meta label="Model">
            {[
              plainName(summary.model.forecaster) && `${plainName(summary.model.forecaster)} forecast`,
              plainName(summary.model.risk_scorer) && `${plainName(summary.model.risk_scorer)} risk scorer`,
            ]
              .filter(Boolean)
              .join(", ") || "Not recorded"}
          </Meta>
        </div>
      ) : query.isError ? (
        <p role="alert" className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          Summary unavailable.
          <Button
            variant="outline"
            className="min-h-11 rounded-full sm:min-h-8"
            disabled={query.isFetching}
            onClick={() => void query.refetch()}
          >
            Try again
          </Button>
        </p>
      ) : (
        <div aria-busy="true" className="flex gap-3">
          <span className="sr-only">Loading summary…</span>
          <Skeleton className="h-6 w-28 rounded-full" />
          <Skeleton className="h-6 w-44 rounded-full" />
          <Skeleton className="h-6 w-56 rounded-full" />
        </div>
      )}
    </header>
  );
}
