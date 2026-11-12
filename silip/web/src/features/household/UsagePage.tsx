import { useQuery } from "@tanstack/react-query";
import { api, unwrap, type Schemas } from "../../shared/api/client";
import { PageHead, QueryView, SimulatedLabel, cn, formatWhen } from "../../shared/ui";
import { Card } from "../../shared/ui/components/card";
import { Skeleton } from "../../shared/ui/components/skeleton";
import { Freshness, useDocumentTitle } from "../../shared/ui/feedback";

const HOURS_PER_POINT = 0.25; // 15-minute readings
const HOURS_PER_DAY = 24;
const POINTS_PER_DAY = HOURS_PER_DAY / HOURS_PER_POINT;

export interface DayUsage {
  day: Date;
  kwh: number;
  /** False when the clamp sent fewer than a full day of readings, so a low total is not a low day. */
  complete: boolean;
}

/** Sums 15-minute kW readings into kWh per local calendar day, oldest first. */
export function dailyKwh(points: Schemas["UsagePoint"][]): DayUsage[] {
  const byDay = new Map<string, { day: Date; kwh: number; readings: number }>();
  for (const point of points) {
    const ts = new Date(point.ts);
    const key = ts.toDateString();
    const entry = byDay.get(key) ?? {
      day: new Date(ts.getFullYear(), ts.getMonth(), ts.getDate()),
      kwh: 0,
      readings: 0,
    };
    entry.kwh += point.kw * HOURS_PER_POINT;
    entry.readings += 1;
    byDay.set(key, entry);
  }
  return [...byDay.values()]
    .sort((a, b) => a.day.getTime() - b.day.getTime())
    .map(({ day, kwh, readings }) => ({ day, kwh, complete: readings >= POINTS_PER_DAY }));
}

function UsageSkeleton() {
  return (
    <Card className="max-w-2xl gap-6 px-6 shadow-none">
      <div className="grid gap-2">
        <Skeleton className="h-4 w-32 rounded" />
        <Skeleton className="h-9 w-40 rounded-lg" />
        <Skeleton className="h-4 w-56 rounded" />
      </div>
      <div className="grid gap-3 border-t pt-4">
        {Array.from({ length: 7 }, (_, i) => (
          <Skeleton key={i} className="h-5 rounded" />
        ))}
      </div>
    </Card>
  );
}

/** The signed-in household's own last 7 days, as daily kWh. */
export function UsagePage() {
  useDocumentTitle("My usage");
  const query = useQuery({
    queryKey: ["me", "usage"],
    queryFn: async () => unwrap(await api.GET("/api/v1/me/usage")),
  });
  return (
    <section>
      <PageHead title="Your usage" lede="Last 7 days, from the clamp in your home. Only you can see this." />
      <QueryView
        {...query}
        isEmpty={(usage) => usage.points.length === 0}
        emptyMessage="No readings from your clamp yet."
        onRetry={query.refetch}
        skeleton={<UsageSkeleton />}
      >
        {(usage) => {
          const days = dailyKwh(usage.points);
          const maxKwh = Math.max(...days.map((d) => d.kwh), 1);
          // Average over the hours actually covered, so a partial first or last day does not drag it down.
          const daysCovered = (usage.points.length * HOURS_PER_POINT) / HOURS_PER_DAY;
          const lastReading = new Date(usage.points[usage.points.length - 1].ts);
          return (
            <Card className="max-w-2xl gap-6 px-6 shadow-none">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Total, last 7 days</p>
                  <p className="font-display text-3xl font-bold">{usage.total_kwh.toFixed(1)} kWh</p>
                  <p className="text-sm text-muted-foreground">
                    About {(usage.total_kwh / daysCovered).toFixed(1)} kWh a day · Last reading{" "}
                    {formatWhen(lastReading)}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <SimulatedLabel show={usage.is_simulated} />
                  <Freshness fetchedAt={query.dataUpdatedAt} dataAsOf={lastReading.toISOString()} />
                </div>
              </div>
              <ul aria-label="Daily usage" className="grid gap-2 border-t pt-4">
                {days.map(({ day, kwh, complete }) => {
                  const date = day.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
                  return (
                    <li
                      key={day.toDateString()}
                      title={`${date}: ${kwh.toFixed(1)} kWh${complete ? "" : ", partial day"}`}
                      className="grid grid-cols-[6.5rem_minmax(0,1fr)_auto] items-center gap-4 text-sm"
                    >
                      <span className="text-muted-foreground">{date}</span>
                      <span aria-hidden="true" className="h-3">
                        <span
                          className={cn(
                            "block h-full min-w-0.5 rounded-r",
                            complete ? "bg-muted-foreground" : "border border-dashed border-muted-foreground",
                          )}
                          style={{ width: `${(100 * kwh) / maxKwh}%` }}
                        />
                      </span>
                      <span className="text-right tabular-nums">
                        <span className="font-semibold">{kwh.toFixed(1)} kWh</span>
                        {!complete && <span className="block text-muted-foreground">partial day</span>}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </Card>
          );
        }}
      </QueryView>
    </section>
  );
}
