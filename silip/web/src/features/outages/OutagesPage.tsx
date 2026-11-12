import { useQuery } from "@tanstack/react-query";
import { CircleCheck, ExternalLink, Loader2, LocateFixed, Search } from "lucide-react";
import { useState, type ReactNode } from "react";
import { REFRESH_INTERVAL_MS, api, unwrap, type Schemas } from "../../shared/api/client";
import { PageHead, QueryView, SimulatedLabel, formatClock } from "../../shared/ui";
import { Button } from "../../shared/ui/components/button";
import { Badge } from "../../shared/ui/components/badge";
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

const STATUS_WORD: Record<Outage["status"], string> = { open: "Power out", restored: "Restored" };

/** One outage: expected time back first, the window once, then cause, start, area and freshness. */
function OutageCard({ outage, distance, fetchedAt }: { outage: Outage; distance: number | null; fetchedAt: number }) {
  const started = new Date(outage.started_at);
  const at = (minutes: number) => formatClock(new Date(started.getTime() + minutes * MS_PER_MIN));
  const name = areaName(outage);
  return (
    <li>
      <Card className="gap-2 px-6 shadow-none">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="font-semibold">{name ?? "Open outage"}</p>
          <Badge variant="secondary" className="px-2.5 font-semibold">
            {STATUS_WORD[outage.status]}
          </Badge>
        </div>
        <p className="font-display text-xl font-bold">Expected back around {at(outage.eta_p50_min)}</p>
        <p className="text-sm text-muted-foreground">
          Window {at(outage.eta_p10_min)} to {at(outage.eta_p90_min)}. This is an estimate.
        </p>
        <dl className="mt-2 grid grid-cols-[repeat(auto-fit,minmax(8rem,1fr))] gap-4 border-t pt-4">
          <Detail label="Cause">{outage.cause}</Detail>
          <Detail label="Started">{formatClock(started)}</Detail>
          <Detail label="Area">
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
        <Freshness fetchedAt={fetchedAt} />
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
    <ul className="grid gap-4">
      {[0, 1].map((i) => (
        <li key={i}>
          <Skeleton className="h-64 rounded-xl" />
        </li>
      ))}
    </ul>
  );
}

function NoOutages({ fetchedAt, where }: { fetchedAt: number; where: "near" | "area" | "all" }) {
  return (
    <Card className="items-start gap-2 px-6 py-8 shadow-none">
      <p className="flex items-center gap-2 font-display text-xl font-bold">
        <CircleCheck aria-hidden="true" className="size-5 shrink-0 text-brand" />
        {where === "near"
          ? "No open outages near you."
          : where === "area"
            ? "No open outages in this area."
            : "No open outages right now."}
      </p>
      <Freshness fetchedAt={fetchedAt} />
      <p className="text-sm text-muted-foreground">If your power is out, report it to Meralco.</p>
    </Card>
  );
}

/**
 * The outage check: "Near me", area search (once the API sends area names) and the results.
 * /outages and the landing page hero both use it, so they answer the same way.
 */
export function OutageCheck() {
  const nearMe = useNearMe();
  const [areaQuery, setAreaQuery] = useState("");
  const query = useQuery({
    queryKey: ["outages", "open"],
    queryFn: async () => unwrap(await api.GET("/api/v1/outages", { params: { query: { status: "open" } } })),
    refetchInterval: REFRESH_INTERVAL_MS,
  });
  const outages = query.data ?? [];
  const searchable = outages.some((o) => areaName(o) !== null);
  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        {searchable && (
          <label className="relative min-w-0 grow sm:max-w-72">
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
              className="h-11 w-full rounded-full border bg-card pr-4 pl-9 text-base placeholder:text-muted-foreground"
            />
          </label>
        )}
        {nearMe.here === null ? (
          <Button className="min-h-11 rounded-full px-5" disabled={nearMe.state === "locating"} onClick={nearMe.locate}>
            {nearMe.state === "locating" ? (
              <Loader2 aria-hidden="true" className="animate-spin" />
            ) : (
              <LocateFixed aria-hidden="true" />
            )}
            {nearMe.state === "locating" ? "Finding you…" : "Near me"}
          </Button>
        ) : (
          <Button variant="outline" className="min-h-11 rounded-full px-5" onClick={nearMe.clear}>
            Newest first
          </Button>
        )}
        {query.data !== undefined && (
          <span className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            {outages.length} open {outages.length === 1 ? "outage" : "outages"}
            {nearMe.here !== null && outages.length > 1 && ", nearest first"}
            <SimulatedLabel show={outages.some((o) => o.is_simulated)} />
          </span>
        )}
      </div>
      <p role="status" className="text-sm text-muted-foreground">
        {nearMe.state === "failed"
          ? "Could not get your location. Check the browser's location setting."
          : nearMe.here !== null
            ? "Your location stays on this device."
            : "Near me asks for your location only when you tap it. It stays on this device."}
      </p>
      <QueryView
        {...query}
        isEmpty={() => false}
        emptyMessage={null}
        onRetry={query.refetch}
        skeleton={<OutagesSkeleton />}
      >
        {(data) => {
          const wanted = areaQuery.trim().toLowerCase();
          const shown = data
            .filter((o) => wanted === "" || (areaName(o) ?? "").toLowerCase().includes(wanted))
            .map((o) => ({
              outage: o,
              distance: nearMe.here === null ? null : distanceKm(nearMe.here, { lat: o.area_lat, lon: o.area_lon }),
            }))
            .sort((a, b) => (a.distance ?? 0) - (b.distance ?? 0));
          if (shown.length === 0) {
            return <NoOutages
                fetchedAt={query.dataUpdatedAt}
                where={wanted !== "" ? "area" : nearMe.here !== null ? "near" : "all"}
              />;
          }
          return (
            <ul className="grid gap-4">
              {shown.map(({ outage, distance }) => (
                <OutageCard
                  key={outage.outage_id}
                  outage={outage}
                  distance={distance}
                  fetchedAt={query.dataUpdatedAt}
                />
              ))}
            </ul>
          );
        }}
      </QueryView>
    </div>
  );
}

/** Public outage view: expected time back first, then cause and area. No household data. */
export function OutagesPage() {
  useDocumentTitle("Outages");
  return (
    <section className="max-w-2xl">
      <PageHead title="Power outages" lede="Open outages and when power is expected back." />
      <OutageCheck />
    </section>
  );
}
