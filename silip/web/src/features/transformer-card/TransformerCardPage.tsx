import { useQuery } from "@tanstack/react-query";
import { Check, ChevronDown, ChevronLeft, ChevronRight, Copy } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { REFRESH_INTERVAL_MS, api, unwrap, type Schemas } from "../../shared/api/client";
import { filterSearch, readFilter, useTransformers, visibleItems } from "../../shared/risk";
import { ActionBadge, PageHead, QueryView, SimulatedLabel, TierBadge, formatPct, formatWhen } from "../../shared/ui";
import { HeatIndexChart } from "../../shared/ui/HeatIndexChart";
import { Button } from "../../shared/ui/components/button";
import { Card } from "../../shared/ui/components/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "../../shared/ui/components/collapsible";
import { Skeleton } from "../../shared/ui/components/skeleton";
import { Freshness, useDocumentTitle } from "../../shared/ui/feedback";
import { ActionBlock, ClampBlock, Drivers, EvBlock } from "./CardBlocks";
import { LoadChart, Sparkline } from "./LoadChart";

// Per viewer: whether they like the load history open. A convenience, so localStorage is fine.
const HISTORY_OPEN_KEY = "silip.card.loadHistoryOpen";
const COPIED_MS = 2000;

/** Highest load_pct among measured (forecast=false) or forecast points; null when there are none. */
function peakLoad(load: Schemas["LoadPoint"][], forecast: boolean): number | null {
  const values = load.filter((p) => p.is_forecast === forecast).map((p) => p.load_pct);
  return values.length === 0 ? null : Math.max(...values);
}

const orNoData = (value: number | null) => (value === null ? "No data" : formatPct(value));

/** "Peak 284% of rating in the next 24 h, 210% in the last 48 h". */
export function historySummary(load: Schemas["LoadPoint"][]): string {
  const next = peakLoad(load, true);
  const last = peakLoad(load, false);
  const nextText =
    next === null ? "No forecast for the next 24 h" : `Peak ${formatPct(next)} of rating in the next 24 h`;
  const lastText = last === null ? "no readings in the last 48 h" : `${formatPct(last)} in the last 48 h`;
  return `${nextText}, ${lastText}`;
}

/** Open unless the viewer closed it before. */
function readHistoryOpen(): boolean {
  try {
    return window.localStorage.getItem(HISTORY_OPEN_KEY) !== "false";
  } catch {
    return true;
  }
}

function saveHistoryOpen(open: boolean) {
  try {
    window.localStorage.setItem(HISTORY_OPEN_KEY, String(open));
  } catch {
    // Storage blocked: the section still opens and closes for this visit.
  }
}

/** One fact in a single hairline-split strip (not a row of separate cards). */
function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="px-6 py-4 shadow-[-1px_-1px_0_var(--border)]">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="font-display text-xl font-bold">{children}</dd>
    </div>
  );
}

function CopyIdButton({ id }: { id: string }) {
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(false), COPIED_MS);
    return () => window.clearTimeout(timer);
  }, [copied]);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(id);
      setCopied(true);
    } catch {
      // Clipboard blocked (http, permissions): the ID is still on screen to select.
    }
  };
  return (
    <Button variant="outline" className="min-h-11 rounded-full sm:min-h-9" onClick={() => void copy()}>
      {copied ? <Check aria-hidden="true" /> : <Copy aria-hidden="true" />}
      <span aria-live="polite">{copied ? "Copied" : "Copy ID"}</span>
    </Button>
  );
}

/** "Dashboard / T-106" plus Previous and Next in the list's current order and filter. */
function CardNav({ transformerId }: { transformerId: string }) {
  const [params] = useSearchParams();
  const filter = readFilter(params);
  const search = filterSearch(filter);
  const list = useTransformers();
  const order = list.data === undefined ? [] : visibleItems(list.data, filter);
  const index = order.findIndex((i) => i.transformer_id === transformerId);
  const prev = index > 0 ? order[index - 1] : undefined;
  const next = index !== -1 && index < order.length - 1 ? order[index + 1] : undefined;
  const step = (item: (typeof order)[number] | undefined, label: string, icon: ReactNode, after: boolean) =>
    item === undefined ? (
      <Button variant="ghost" className="min-h-11 rounded-full sm:min-h-9" disabled>
        {!after && icon}
        {label}
        {after && icon}
      </Button>
    ) : (
      <Button asChild variant="ghost" className="min-h-11 rounded-full sm:min-h-9">
        <Link
          to={`/engineer/transformers/${encodeURIComponent(item.transformer_id)}${search}`}
          aria-label={`${label}: ${item.transformer_id}`}
        >
          {!after && icon}
          {item.transformer_id}
          {after && icon}
        </Link>
      </Button>
    );
  return (
    <div className="flex flex-wrap items-center justify-between gap-2">
      <nav aria-label="Breadcrumb">
        <ol className="flex items-center gap-2 text-sm">
          <li>
            <Link
              to={`/engineer${search}`}
              className="inline-flex min-h-11 items-center font-semibold text-muted-foreground no-underline hover:text-foreground sm:min-h-0"
            >
              Dashboard
            </Link>
          </li>
          <li aria-hidden="true" className="text-muted-foreground">
            /
          </li>
          <li aria-current="page" className="font-semibold">
            {transformerId}
          </li>
        </ol>
      </nav>
      {index !== -1 && (
        <div className="flex items-center gap-1">
          {step(prev, "Previous", <ChevronLeft aria-hidden="true" />, false)}
          <span className="text-sm text-muted-foreground tabular-nums">
            {index + 1} of {order.length}
          </span>
          {step(next, "Next", <ChevronRight aria-hidden="true" />, true)}
        </div>
      )}
    </div>
  );
}

function LoadHistory({ card }: { card: Schemas["TransformerCard"] }) {
  const [open, setOpen] = useState(readHistoryOpen);
  return (
    <Collapsible
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        saveHistoryOpen(next);
      }}
    >
      <Card id="load" tabIndex={-1} className="gap-0 py-0 shadow-none outline-none">
        <h2 className="text-xl">
          <CollapsibleTrigger className="group flex min-h-16 w-full flex-wrap items-center gap-x-4 gap-y-1 rounded-xl px-6 py-4 text-left">
            <span>Load and heat index</span>
            <span className="font-sans text-sm font-normal text-muted-foreground">{historySummary(card.load)}</span>
            <span className="ml-auto flex items-center gap-3">
              {card.load.length > 1 && <Sparkline points={card.load} />}
              <ChevronDown
                aria-hidden="true"
                className="size-5 text-muted-foreground transition-transform duration-150 group-data-[state=open]:rotate-180"
              />
            </span>
          </CollapsibleTrigger>
        </h2>
        <CollapsibleContent>
          <div className="border-t px-6 py-6">
            {card.load.length === 0 ? (
              <p className="text-sm text-muted-foreground">No load readings for this transformer yet.</p>
            ) : (
              <div className="grid gap-6">
                <LoadChart points={card.load} ratedKva={card.rated_kva} />
                {/* Its own scale under the same time axis: two measures never share one y-axis. */}
                {(card.weather ?? []).some((h) => h.heat_index_c !== null) ? (
                  <HeatIndexChart
                    hours={(card.weather ?? []).map((h) => ({
                      ts: h.ts,
                      heatC: h.heat_index_c,
                      rainMm: h.precipitation_mm,
                    }))}
                    domain={[new Date(card.load[0].ts).getTime(), new Date(card.load[card.load.length - 1].ts).getTime()]}
                  />
                ) : (
                  <p className="text-sm text-muted-foreground">No heat-index forecast for this transformer yet.</p>
                )}
              </div>
            )}
          </div>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}

function CardSkeleton() {
  return (
    <div className="grid gap-6">
      <div className="grid gap-2">
        <Skeleton className="h-10 w-40 rounded-lg" />
        <Skeleton className="h-5 w-64 rounded-lg" />
      </div>
      <Skeleton className="h-20 rounded-xl" />
      <Skeleton className="h-40 rounded-xl" />
      <Skeleton className="h-16 rounded-xl" />
    </div>
  );
}

/** One transformer: tier, all reasons, then load history on request. Decision support only. */
export function TransformerCardPage() {
  const { transformerId = "" } = useParams();
  useDocumentTitle(transformerId, "Dashboard");
  const query = useQuery({
    queryKey: ["transformer", transformerId],
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/transformers/{transformer_id}", { params: { path: { transformer_id: transformerId } } }),
      ),
    refetchInterval: REFRESH_INTERVAL_MS,
  });
  return (
    <section className="grid gap-6">
      <CardNav transformerId={transformerId} />
      <QueryView {...query} isEmpty={() => false} emptyMessage="" onRetry={query.refetch} skeleton={<CardSkeleton />}>
        {(card) => (
          <>
            <PageHead className="mb-0" title={card.transformer_id} lede={`Rated ${card.rated_kva} kVA`}>
              <div className="flex flex-wrap items-center gap-2">
                <TierBadge tier={card.risk.tier} />
                {card.action != null && <ActionBadge action={card.action} />}
                <SimulatedLabel show={card.is_simulated} />
                <Freshness fetchedAt={query.dataUpdatedAt} dataAsOf={card.as_of} />
                <span className="sm:ml-auto">
                  <CopyIdButton id={card.transformer_id} />
                </span>
              </div>
            </PageHead>

            <dl className="m-0 grid grid-cols-[repeat(auto-fit,minmax(8.5rem,1fr))] overflow-hidden rounded-xl border bg-card">
              <Fact label="Peak next 24 h, of rating">{orNoData(peakLoad(card.load, true))}</Fact>
              <Fact label="Peak time">{card.peak_ts == null ? "No data" : formatWhen(new Date(card.peak_ts))}</Fact>
              <Fact label="Heat index max">
                {card.heat_index_max_c == null ? "No forecast" : `${card.heat_index_max_c.toFixed(1)} °C`}
              </Fact>
              <Fact label="Coverage">{formatPct(card.risk.coverage_pct)} of homes</Fact>
              <Fact label="Confidence">{formatPct(card.risk.confidence)}</Fact>
            </dl>

            <ActionBlock card={card} />
            <Drivers card={card} />
            <LoadHistory card={card} />

            <div className="grid gap-6 md:grid-cols-2">
              <ClampBlock card={card} />
              <EvBlock card={card} />
            </div>

            <p className="max-w-2xl text-sm text-muted-foreground">
              Decision support only. An engineer decides what to do. Confidence depends on how many homes are metered.
            </p>
          </>
        )}
      </QueryView>
    </section>
  );
}
