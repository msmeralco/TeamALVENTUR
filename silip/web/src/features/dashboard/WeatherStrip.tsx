import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import type { Schemas } from "../../shared/api/client";
import type { TransformerItem } from "../../shared/risk";
import type { PeakMark } from "../../shared/ui/HeatIndexChart";
import { QueryView, SimulatedLabel, cn } from "../../shared/ui";
import { Button } from "../../shared/ui/components/button";
import { Card } from "../../shared/ui/components/card";
import { Skeleton } from "../../shared/ui/components/skeleton";
import { formatStamp, WeatherBadge } from "./SummaryRow";
import { HEAT_SOURCE, currentHour, heatCategory, isHeatWarning, peakHour, relativeWhen } from "./heat";
import { useOutlook } from "./queries";
import { WeatherChart } from "./WeatherChart";

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

/** No hours to draw: nothing fetched yet, or the stored forecast is too old to use. */
export function hasForecast(outlook: Pick<Outlook, "status" | "hours">): boolean {
  return outlook.status !== "missing" && outlook.hours.length > 0;
}

/** Each queued Critical transformer's forecast peak, for marking on the heat-index line. */
export function criticalPeaks(items: TransformerItem[]): PeakMark[] {
  return items
    .filter((i) => i.risk.tier === "Critical" && i.peak_ts != null)
    .map((i) => ({ ts: i.peak_ts as string, ids: [i.transformer_id] }));
}

// Per browser: a hidden weather panel stays hidden, so the map keeps its space.
const WEATHER_KEY = "silip.dashboard.weather";

function readWeatherOpen(): boolean {
  try {
    return window.localStorage.getItem(WEATHER_KEY) !== "hidden";
  } catch {
    return true;
  }
}

function rememberWeatherOpen(open: boolean) {
  try {
    window.localStorage.setItem(WEATHER_KEY, open ? "shown" : "hidden");
  } catch {
    // Storage blocked: the panel just opens next time.
  }
}

/** "Heat index 34 °C · Extreme caution", from the hour holding now. Null without a value. */
export function heatNowText(hours: Outlook["hours"], nowMs: number): { text: string; warn: boolean } | null {
  const c = currentHour(hours, nowMs)?.heat_index_max_c;
  if (c == null) return null;
  return { text: `Heat index ${Math.round(c)} °C · ${heatCategory(c)}`, warn: isHeatWarning(c) };
}

/** Heat index now with its NOAA word as color plus word: Danger and up take the Watch color. */
export function HeatChip({ outlook }: { outlook: Outlook | undefined }) {
  const now = outlook !== undefined && hasForecast(outlook) ? heatNowText(outlook.hours, Date.now()) : null;
  return (
    <span
      title={HEAT_SOURCE}
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-sm font-semibold whitespace-nowrap",
        now?.warn ? "bg-watch-soft text-watch" : "bg-secondary text-secondary-foreground",
      )}
    >
      {outlook === undefined ? "Heat index loading" : (now?.text ?? "No forecast loaded yet")}
    </span>
  );
}

/** Now, temperature and the 48 h peak in one line. */
function WeatherSummaryLine({ outlook, nowMs }: { outlook: Outlook; nowMs: number }) {
  const hour = currentHour(outlook.hours, nowMs);
  const peak = peakHour(outlook.hours);
  return (
    <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
      <HeatChip outlook={outlook} />
      {hour?.temperature_max_c != null && (
        <span className="tabular-nums">
          <span className="text-muted-foreground">Temperature</span> {Math.round(hour.temperature_max_c)} °C
        </span>
      )}
      {peak?.heat_index_max_c != null && (
        <span className="font-semibold tabular-nums">
          Peak heat index {Math.round(peak.heat_index_max_c)} °C at {relativeWhen(peak.ts, nowMs)}
        </span>
      )}
    </p>
  );
}

/**
 * Weather for the transformers in view: heat index now and its 48 h line over NOAA bands, rain and
 * the Critical peaks. Collapsible; on wide screens it docks under the map.
 */
export function WeatherStrip({ items, docked = false }: { items: TransformerItem[]; docked?: boolean }) {
  const query = useOutlook();
  const [open, setOpen] = useState(readWeatherOpen);
  const nowMs = Date.now();
  const toggle = () => {
    setOpen(!open);
    rememberWeatherOpen(!open);
  };
  const outlook = query.data;
  return (
    <section
      aria-labelledby="weather-title"
      className={cn(docked ? "overflow-y-auto border-t bg-card px-4 py-3 lg:max-h-[50%]" : "px-4 py-6 sm:px-6")}
    >
      <Card className={cn("gap-3 shadow-none", docked ? "border-0 bg-transparent p-0" : "px-6 py-5")}>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <h2 id="weather-title" className="text-xl">
            Heat index, next 48 h
          </h2>
          {outlook !== undefined && (
            <>
              <WeatherBadge status={outlook.status} />
              <SimulatedLabel show={outlook.is_simulated} />
            </>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="ml-auto min-h-11 rounded-full text-muted-foreground sm:min-h-8"
            aria-expanded={open}
            aria-controls="weather-body"
            onClick={toggle}
          >
            {open ? <ChevronDown aria-hidden="true" /> : <ChevronUp aria-hidden="true" />}
            {open ? "Hide weather" : "Show weather"}
          </Button>
        </div>
        {outlook !== undefined && hasForecast(outlook) && !open && (
          <WeatherSummaryLine outlook={outlook} nowMs={nowMs} />
        )}
        <div id="weather-body" hidden={!open}>
          <QueryView
            {...query}
            isEmpty={() => false}
            emptyMessage=""
            onRetry={query.refetch}
            skeleton={<Skeleton className="h-36 rounded-xl" />}
          >
            {(data) => (
              <div className="grid gap-3">
                {hasForecast(data) && peakHour(data.hours) !== undefined ? (
                  <>
                    <WeatherSummaryLine outlook={data} nowMs={nowMs} />
                    <p className="text-sm">{outlookStatusText(data)}</p>
                    {data.note != null && <p className="text-sm text-muted-foreground">{data.note}.</p>}
                    <WeatherChart hours={data.hours} marks={criticalPeaks(items)} nowMs={nowMs} />
                    <p className="text-sm text-muted-foreground">
                      Hottest hour across the weather cells in view. Source: {data.source}. {HEAT_SOURCE}.
                    </p>
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground">No forecast loaded yet.</p>
                )}
              </div>
            )}
          </QueryView>
        </div>
      </Card>
    </section>
  );
}
