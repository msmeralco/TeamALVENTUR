import { useQuery } from "@tanstack/react-query";
import { ExternalLink, Loader2, LocateFixed, Search } from "lucide-react";
import { useState, type ReactNode } from "react";
import { REFRESH_INTERVAL_MS, api, unwrap, type Schemas } from "../../shared/api/client";
import { PageHead, QueryView, SimulatedLabel, formatClock } from "../../shared/ui";
import { Button } from "../../shared/ui/components/button";
import { Card } from "../../shared/ui/components/card";
import { Skeleton } from "../../shared/ui/components/skeleton";
import { Freshness, useDocumentTitle } from "../../shared/ui/feedback";

type Outage = Schemas["OutageSummary"];
type Here = { lat: number; lon: number };

const MS_PER_MIN = 60_000;
const EARTH_RADIUS_KM = 6371;
const LOCATE_TIMEOUT_MS = 10_000;

/** Great-circle distance in km. Runs on the device; the location is never sent anywhere. */
export function distanceKm(a: Here, b: Here): number {
  const rad = (deg: number) => (deg * Math.PI) / 180;
  const dLat = rad(b.lat - a.lat);
  const dLon = rad(b.lon - a.lon);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_KM * Math.asin(Math.sqrt(h));
}

/** The area name, once the API sends one (API ask: `area_name`). Until then, null and the search stays hidden. */
function areaName(outage: Outage): string | null {
  return "area_name" in outage && typeof outage.area_name === "string" ? outage.area_name : null;
}

function Detail({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="font-semibold first-letter:uppercase">{children}</dd>
    </div>
  );
}

function OutageCard({ outage, distance }: { outage: Outage; distance: number | null }) {
  const started = new Date(outage.started_at);
  const at = (minutes: number) => formatClock(new Date(started.getTime() + minutes * MS_PER_MIN));
  const name = areaName(outage);
  return (
    <li>
      <Card className="gap-2 px-6 shadow-none">
        <p className="text-sm font-semibold text-muted-foreground">Power expected back</p>
        <p className="font-display text-3xl font-bold">
          {at(outage.eta_p10_min)} to {at(outage.eta_p90_min)}
        </p>
        <p>
          Most likely around <strong>{at(outage.eta_p50_min)}</strong>. This is an estimate.
        </p>
        <dl className="mt-2 grid grid-cols-[repeat(auto-fit,minmax(9rem,1fr))] gap-4 border-t pt-4">
          <Detail label="Cause">{outage.cause}</Detail>
          <Detail label="Started">{formatClock(started)}</Detail>
          <Detail label="Area">
            {name !== null && <span className="block">{name}</span>}
            <a
              className="inline-flex min-h-11 items-center underline underline-offset-4 sm:min-h-0"
              href={`https://www.openstreetmap.org/?mlat=${outage.area_lat}&mlon=${outage.area_lon}#map=16/${outage.area_lat}/${outage.area_lon}`}
              target="_blank"
              rel="noreferrer"
            >
              See on map
              <ExternalLink aria-hidden="true" className="ml-1 size-3.5" />
              <span className="sr-only"> (opens in a new tab)</span>
            </a>
            {distance !== null && (
              <span className="block text-sm font-normal text-muted-foreground">
                About {distance < 1 ? "<1" : distance.toFixed(1)} km from you
              </span>
            )}
          </Detail>
        </dl>
      </Card>
    </li>
  );
}

/** "Near me": asks the browser for a position once and keeps it in memory on this page only. */
function useNearMe() {
  const [here, setHere] = useState<Here | null>(null);
  const [state, setState] = useState<"idle" | "locating" | "failed">("idle");
  const locate = () => {
    if (!("geolocation" in navigator)) {
      setState("failed");
      return;
    }
    setState("locating");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setHere({ lat: position.coords.latitude, lon: position.coords.longitude });
        setState("idle");
      },
      () => setState("failed"),
      { timeout: LOCATE_TIMEOUT_MS, maximumAge: 5 * MS_PER_MIN },
    );
  };
  return { here, state, locate, clear: () => setHere(null) };
}

function OutagesSkeleton() {
  return (
    <ul className="grid max-w-2xl gap-4">
      {[0, 1].map((i) => (
        <li key={i}>
          <Skeleton className="h-60 rounded-xl" />
        </li>
      ))}
    </ul>
  );
}

/** Public outage view: restoration range first, then cause and area. No household data. */
export function OutagesPage() {
  useDocumentTitle("Outages");
  const nearMe = useNearMe();
  const [areaQuery, setAreaQuery] = useState("");
  const query = useQuery({
    queryKey: ["outages", "open"],
    queryFn: async () => unwrap(await api.GET("/api/v1/outages", { params: { query: { status: "open" } } })),
    refetchInterval: REFRESH_INTERVAL_MS,
  });
  return (
    <section>
      <PageHead title="Power outages" lede="Open outages and when power is expected back.">
        {query.data !== undefined && (
          <div className="flex flex-wrap items-center gap-2">
            <SimulatedLabel show={query.data.some((o) => o.is_simulated)} />
            <Freshness fetchedAt={query.dataUpdatedAt} />
          </div>
        )}
      </PageHead>
      <QueryView
        {...query}
        isEmpty={(outages) => outages.length === 0}
        emptyMessage="No open outages right now. If your power is out, report it to Meralco."
        onRetry={query.refetch}
        skeleton={<OutagesSkeleton />}
      >
        {(outages) => {
          const searchable = outages.some((o) => areaName(o) !== null);
          const wanted = areaQuery.trim().toLowerCase();
          const shown = outages
            .filter((o) => wanted === "" || (areaName(o) ?? "").toLowerCase().includes(wanted))
            .map((o) => ({
              outage: o,
              distance: nearMe.here === null ? null : distanceKm(nearMe.here, { lat: o.area_lat, lon: o.area_lon }),
            }))
            .sort((a, b) => (a.distance ?? 0) - (b.distance ?? 0));
          return (
            <div className="grid max-w-2xl gap-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="mr-auto text-sm text-muted-foreground">
                  {outages.length} open {outages.length === 1 ? "outage" : "outages"}
                  {nearMe.here !== null && ", nearest first"}
                </span>
                {searchable && (
                  <label className="relative min-w-0 grow sm:max-w-64">
                    <span className="sr-only">Search by area</span>
                    <Search
                      aria-hidden="true"
                      className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
                    />
                    <input
                      type="search"
                      placeholder="Search your area"
                      value={areaQuery}
                      onChange={(e) => setAreaQuery(e.target.value)}
                      className="h-11 w-full rounded-full border bg-card pr-4 pl-9 text-base placeholder:text-muted-foreground sm:h-9 sm:text-sm"
                    />
                  </label>
                )}
                {nearMe.here === null ? (
                  <Button
                    variant="outline"
                    className="min-h-11 rounded-full sm:min-h-9"
                    disabled={nearMe.state === "locating"}
                    onClick={nearMe.locate}
                  >
                    {nearMe.state === "locating" ? (
                      <Loader2 aria-hidden="true" className="animate-spin" />
                    ) : (
                      <LocateFixed aria-hidden="true" />
                    )}
                    {nearMe.state === "locating" ? "Finding you…" : "Near me"}
                  </Button>
                ) : (
                  <Button variant="outline" className="min-h-11 rounded-full sm:min-h-9" onClick={nearMe.clear}>
                    Newest first
                  </Button>
                )}
              </div>
              <p role="status" className="text-sm text-muted-foreground empty:hidden">
                {nearMe.state === "failed"
                  ? "Could not get your location. Check the browser's location setting."
                  : nearMe.here !== null
                    ? "Your location stays on this device."
                    : ""}
              </p>
              {shown.length === 0 ? (
                <Card className="items-start gap-3 px-6 py-8">
                  <p>No open outages match that area.</p>
                  <Button
                    variant="outline"
                    className="min-h-11 rounded-full sm:min-h-9"
                    onClick={() => setAreaQuery("")}
                  >
                    Clear search
                  </Button>
                </Card>
              ) : (
                <ul className="grid gap-4">
                  {shown.map(({ outage, distance }) => (
                    <OutageCard key={outage.outage_id} outage={outage} distance={distance} />
                  ))}
                </ul>
              )}
            </div>
          );
        }}
      </QueryView>
    </section>
  );
}
