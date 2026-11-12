import { List, Map as MapIcon, PanelLeftClose, PanelLeftOpen, Search } from "lucide-react";
import { lazy, Suspense, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  TIERS,
  clampCounts,
  filterSearch,
  readFilter,
  useClamps,
  useTransformers,
  visibleItems,
  type ListFilter,
  type Tier,
  type TransformerItem,
} from "../../shared/risk";
import { ActionBadge, QueryView, SimulatedLabel, TierBadge, cn, formatPct, formatWhen } from "../../shared/ui";
import { Button } from "../../shared/ui/components/button";
import { Card } from "../../shared/ui/components/card";
import { Skeleton } from "../../shared/ui/components/skeleton";
import { ErrorBoundary, Freshness, useDocumentTitle } from "../../shared/ui/feedback";
import { EvLegend, RiskLegend } from "./MapLegends";
import { useChargers, useCoverage } from "./queries";
import { SummaryRow } from "./SummaryRow";
import { AREA_MIN_ZOOM, RING_MIN_ZOOM, type CoverageBands, type Overlay } from "./overlays";
import { WeatherStrip } from "./WeatherStrip";

// MapLibre is large; load it only when the dashboard opens.
const TransformerMap = lazy(() => import("./TransformerMap").then((m) => ({ default: m.TransformerMap })));

const WIDE_SCREEN = "(min-width: 64rem)"; // Tailwind `lg`: queue and map side by side
// Per tab, so coming back from a card lands on the row you opened.
const LAST_OPENED_KEY = "silip.riskMap.lastOpened";
const TIER_DOT: Record<Tier, string> = { Critical: "bg-critical", Watch: "bg-watch", OK: "bg-ok" };
const OVERLAYS: { value: Overlay; label: string }[] = [
  { value: "risk", label: "Risk" },
  { value: "coverage", label: "Clamp coverage" },
  { value: "ev", label: "EV chargers" },
];

function useMediaQuery(query: string): boolean {
  const get = () => typeof window.matchMedia === "function" && window.matchMedia(query).matches;
  const [matches, setMatches] = useState(get);
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const media = window.matchMedia(query);
    const onChange = () => setMatches(media.matches);
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, [query]);
  return matches;
}

function readLastOpened(): string | null {
  try {
    return window.sessionStorage.getItem(LAST_OPENED_KEY);
  } catch {
    return null;
  }
}

function rememberLastOpened(id: string) {
  try {
    window.sessionStorage.setItem(LAST_OPENED_KEY, id);
  } catch {
    // Storage blocked: the list just starts at the top.
  }
}

// Wide screens can hide the queue panel to give the map the full width. A per-browser convenience.
const PANEL_KEY = "silip.dashboard.panel";

function readPanelOpen(): boolean {
  try {
    return window.localStorage.getItem(PANEL_KEY) !== "hidden";
  } catch {
    return true;
  }
}

function rememberPanelOpen(open: boolean) {
  try {
    window.localStorage.setItem(PANEL_KEY, open ? "shown" : "hidden");
  } catch {
    // Storage blocked: the panel just opens next time.
  }
}

const isPeakReason = (reason: string) => reason.startsWith("Peak forecast");

/** The top reason, unless it only repeats the peak already on the row; then the next one. */
export function rowReason(item: TransformerItem): string {
  const top = item.top_reason ?? item.risk.reasons[0];
  if (top === undefined) return "No reason given.";
  return isPeakReason(top) ? (item.risk.reasons.find((r) => !isPeakReason(r)) ?? top) : top;
}

function peakText(item: TransformerItem): string {
  const pct = formatPct(item.risk.peak_load_pct);
  return item.peak_ts == null ? `Peak ${pct} in the next 24 h` : `Peak ${pct} at ${formatWhen(new Date(item.peak_ts))}`;
}

interface RowProps {
  item: TransformerItem;
  href: string;
  active: boolean;
  lastOpened: boolean;
  onHover: (id: string | null) => void;
  onFocusRow: (id: string) => void;
}

function QueueRow({ item, href, active, lastOpened, onHover, onFocusRow }: RowProps) {
  const { risk } = item;
  return (
    <li
      id={`row-${item.transformer_id}`}
      onMouseEnter={() => onHover(item.transformer_id)}
      onMouseLeave={() => onHover(null)}
    >
      <Link
        to={href}
        onClick={() => rememberLastOpened(item.transformer_id)}
        onFocus={() => onFocusRow(item.transformer_id)}
        onBlur={() => onHover(null)}
        className={cn(
          "grid gap-1 rounded-xl px-3 py-3 text-foreground no-underline transition-colors duration-150 hover:bg-accent",
          active && "bg-accent",
          lastOpened && "ring-2 ring-ring/40",
        )}
      >
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="mr-1 text-base font-bold">{item.transformer_id}</h3>
          <TierBadge tier={risk.tier} />
          {item.action != null && <ActionBadge action={item.action} />}
          {lastOpened && <span className="text-sm text-muted-foreground">Last opened</span>}
        </div>
        <p className="text-sm font-semibold tabular-nums">{peakText(item)}</p>
        <p className="text-sm">{rowReason(item)}</p>
        <p className="text-sm text-muted-foreground tabular-nums">
          Coverage {formatPct(risk.coverage_pct)} | Confidence {formatPct(risk.confidence)}
        </p>
      </Link>
    </li>
  );
}

function FilterChip({ pressed, onClick, children }: { pressed: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      onClick={onClick}
      className={cn(
        "inline-flex min-h-11 items-center gap-2 rounded-full border bg-card px-3.5 text-sm font-semibold transition-colors duration-150 hover:bg-accent sm:min-h-9",
        pressed && "border-foreground bg-selected text-selected-foreground hover:bg-selected",
      )}
    >
      {children}
    </button>
  );
}

function Toolbar({
  items,
  filter,
  setFilter,
}: {
  items: TransformerItem[];
  filter: ListFilter;
  setFilter: (next: Partial<ListFilter>, replace?: boolean) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <div role="group" aria-label="Filter by tier" className="flex flex-wrap gap-2">
        <FilterChip pressed={filter.tier === null} onClick={() => setFilter({ tier: null })}>
          All <span className="tabular-nums">{items.length}</span>
        </FilterChip>
        {TIERS.map((tier) => (
          <FilterChip
            key={tier}
            pressed={filter.tier === tier}
            onClick={() => setFilter({ tier: filter.tier === tier ? null : tier })}
          >
            <span aria-hidden="true" className={cn("size-2 rounded-full", TIER_DOT[tier])} />
            {tier} <span className="tabular-nums">{items.filter((i) => i.risk.tier === tier).length}</span>
          </FilterChip>
        ))}
      </div>
      <label className="relative min-w-0 grow sm:max-w-64">
        <span className="sr-only">Find a transformer by ID</span>
        <Search
          aria-hidden="true"
          className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
        />
        <input
          type="search"
          inputMode="search"
          autoComplete="off"
          placeholder="Find ID, like T-106"
          value={filter.query}
          onChange={(e) => setFilter({ query: e.target.value }, true)}
          className="h-11 w-full rounded-full border bg-card pr-4 pl-9 text-base placeholder:text-muted-foreground sm:h-9 sm:text-sm"
        />
      </label>
    </div>
  );
}

function QueueSkeleton() {
  return (
    <div className="grid gap-3">
      {[0, 1, 2, 3].map((i) => (
        <Skeleton key={i} className="h-24 rounded-xl" />
      ))}
    </div>
  );
}

/**
 * Ranked by action (Inspect before peak first). Monitor rows wait behind a button unless you filtered,
 * searched or came back from one of them.
 */
function Queue({
  visible,
  filtered,
  lastOpened,
  activeId,
  hrefFor,
  onHover,
  onFocusRow,
  onClear,
}: {
  visible: TransformerItem[];
  filtered: boolean;
  lastOpened: string | null;
  activeId: string | null;
  hrefFor: (id: string) => string;
  onHover: (id: string | null) => void;
  onFocusRow: (id: string) => void;
  onClear: () => void;
}) {
  const quiet = visible.filter((i) => i.action === "Monitor" || i.action == null);
  const [showQuiet, setShowQuiet] = useState(() => quiet.some((i) => i.transformer_id === lastOpened));
  if (visible.length === 0) {
    return (
      <Card className="items-start gap-3 px-6 py-8 shadow-none">
        <p>No transformers match this filter.</p>
        <Button variant="outline" className="min-h-11 rounded-full sm:min-h-9" onClick={onClear}>
          Clear filter
        </Button>
      </Card>
    );
  }
  const shown = filtered || showQuiet ? visible : visible.filter((i) => !quiet.includes(i));
  const hidden = visible.length - shown.length;
  return (
    <div className="grid gap-2">
      <ol aria-label="Action queue, most urgent first" className="grid gap-1">
        {shown.map((item) => (
          <QueueRow
            key={item.transformer_id}
            item={item}
            href={hrefFor(item.transformer_id)}
            active={item.transformer_id === activeId}
            lastOpened={item.transformer_id === lastOpened}
            onHover={onHover}
            onFocusRow={onFocusRow}
          />
        ))}
      </ol>
      {hidden > 0 && (
        <Button
          variant="outline"
          className="min-h-11 justify-self-start rounded-full sm:min-h-9"
          onClick={() => setShowQuiet(true)}
        >
          Show {hidden} to monitor
        </Button>
      )}
    </div>
  );
}

/** Risk, clamp coverage or EV chargers; one overlay at a time. */
function OverlayControl({ value, onChange }: { value: Overlay; onChange: (next: Overlay) => void }) {
  return (
    <div
      role="radiogroup"
      aria-label="Map overlay"
      className="flex rounded-full border bg-card p-1 shadow-lg"
      onKeyDown={(e) => {
        const step = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
        if (step === 0) return;
        e.preventDefault();
        const index = OVERLAYS.findIndex((o) => o.value === value);
        const next = OVERLAYS[(index + step + OVERLAYS.length) % OVERLAYS.length];
        onChange(next.value);
        e.currentTarget.querySelector<HTMLButtonElement>(`[data-value="${next.value}"]`)?.focus();
      }}
    >
      {OVERLAYS.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          data-value={o.value}
          aria-checked={value === o.value}
          tabIndex={value === o.value ? 0 : -1}
          onClick={() => onChange(o.value)}
          className={cn(
            "min-h-11 rounded-full px-3 text-sm font-semibold whitespace-nowrap text-muted-foreground transition-colors duration-150 hover:text-foreground sm:min-h-8",
            value === o.value && "bg-selected text-selected-foreground",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

const pill = "rounded-full bg-card/90 px-2.5 py-0.5 text-xs text-muted-foreground";

function RetryNote({ text, onRetry }: { text: string; onRetry: () => void }) {
  return (
    <p role="status" className={cn(pill, "pointer-events-auto flex items-center gap-2 py-0.5 pr-1")}>
      {text}
      <Button variant="outline" className="h-7 rounded-full px-3 text-xs" onClick={onRetry}>
        Retry
      </Button>
    </p>
  );
}

/**
 * Engineer decision dashboard: the summary row, then the action queue beside the map (one at a time on
 * phones, list first), then the 48 h heat-index strip.
 */
export function DashboardPage() {
  useDocumentTitle("Dashboard");
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const filter = readFilter(params);
  const query = useTransformers();
  const clampQuery = useClamps();
  const coverage = useCoverage();
  const [overlay, setOverlay] = useState<Overlay>("risk");
  const [evOpened, setEvOpened] = useState(false);
  const chargers = useChargers(evOpened);
  const wide = useMediaQuery(WIDE_SCREEN);
  const [hoverId, setHoverId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [focusId, setFocusId] = useState<string | null>(null);
  // Phones show one at a time, and the queue leads: it answers "what do I do first".
  const [phoneView, setPhoneView] = useState<"list" | "map">("list");
  const [lastOpened] = useState(readLastOpened);
  const [panelOpen, setPanelOpen] = useState(readPanelOpen);
  const restored = useRef(false);
  const loadFailed = query.data === undefined && !query.isPending;
  const panelHidden = wide && !panelOpen && !loadFailed;
  const listShown = !panelHidden && (loadFailed || wide || phoneView === "list");
  const togglePanel = (open: boolean) => {
    setPanelOpen(open);
    rememberPanelOpen(open);
  };
  const mapShown = wide || phoneView === "map";

  const coverageData = coverage.data;
  const bands = useMemo<CoverageBands | null>(
    () =>
      coverageData === undefined
        ? null
        : { minTrust: coverageData.min_trust_reporting, target: coverageData.target_coverage },
    [coverageData],
  );
  const stations = useMemo(() => chargers.data?.stations ?? [], [chargers.data]);

  const chooseOverlay = (next: Overlay) => {
    setOverlay(next);
    if (next === "ev") setEvOpened(true);
  };

  const setFilter = (next: Partial<ListFilter>, replace = false) => {
    if ("query" in next) {
      setHoverId(null);
      setSelectedId(null);
    }
    setParams(new URLSearchParams(filterSearch({ ...filter, ...next })), { replace });
  };
  const hrefFor = (id: string) => `/engineer/transformers/${encodeURIComponent(id)}${filterSearch(filter)}`;

  // Back from a card: bring the row you opened into view once (in the queue's own scroll).
  useEffect(() => {
    if (restored.current || query.data === undefined || lastOpened === null || !listShown) return;
    restored.current = true;
    document.getElementById(`row-${lastOpened}`)?.scrollIntoView?.({ block: "center" });
  }, [query.data, lastOpened, listShown]);

  // A pin tapped on the map: show its row in the queue too.
  useEffect(() => {
    if (selectedId !== null && wide) {
      document.getElementById(`row-${selectedId}`)?.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
    }
  }, [selectedId, wide]);

  const items = query.data ?? [];
  const visible = visibleItems(items, filter);
  const filtered = filter.tier !== null || filter.query.trim() !== "";
  const shownIds = new Set(visible.map((i) => i.transformer_id));
  const searchFocusId = filter.query.trim() !== "" && visible.length === 1 ? visible[0].transformer_id : null;
  const inspect = items.filter((i) => i.action === "Inspect before peak").length;
  const clamps = clampQuery.data?.clamps ?? [];
  const counts = clampCounts(clamps);

  // Once search narrows to one transformer, bring it into view.
  useEffect(() => {
    setFocusId(searchFocusId);
  }, [searchFocusId]);

  const legend = (zoom: number): ReactNode => {
    if (overlay === "coverage") {
      if (coverage.isError && bands === null) {
        return <RetryNote text="Clamp coverage unavailable" onRetry={() => void coverage.refetch()} />;
      }
      if (bands === null) return <p className={pill}>Loading clamp coverage…</p>;
      return (
        <div className="grid gap-1 rounded-xl bg-card/90 px-2.5 py-1.5 text-xs text-muted-foreground">
          <span className="font-semibold text-foreground">Homes reporting</span>
          <span className="flex items-center gap-2">
            <span aria-hidden="true" className="size-3 rounded-sm bg-brand/55" />
            {formatPct(bands.target)} or more: at target
          </span>
          <span className="flex items-center gap-2">
            <span aria-hidden="true" className="size-3 rounded-sm bg-brand/30" />
            {formatPct(bands.minTrust)} to {formatPct(bands.target)}: below target
          </span>
          <span className="flex items-center gap-2">
            <span aria-hidden="true" className="size-3 rounded-sm bg-muted-foreground/20" />
            Under {formatPct(bands.minTrust)}: too few to trust
          </span>
          <span className="flex items-center gap-2">
            <span aria-hidden="true" className="size-3 rounded-sm border border-muted-foreground" />
            Outline only: no clamp data
          </span>
          {zoom < AREA_MIN_ZOOM && <span>Zoom in to see areas</span>}
          <SimulatedLabel show={coverage.data?.is_simulated ?? false} />
        </div>
      );
    }
    if (overlay === "ev") {
      if (chargers.isError && chargers.data === undefined) {
        return <RetryNote text="EV chargers unavailable" onRetry={() => void chargers.refetch()} />;
      }
      if (chargers.data === undefined) return <p className={pill}>Loading EV chargers…</p>;
      const km = chargers.data.radius_m / 1000;
      return (
        <div className="grid gap-1 rounded-xl bg-card/90 px-2.5 py-1.5 text-xs text-muted-foreground">
          <EvLegend reach={`${km} km reach${zoom < RING_MIN_ZOOM ? " (zoom in to see)" : ""}`} />
          <SimulatedLabel show={chargers.data.is_simulated} />
        </div>
      );
    }
    return <RiskLegend />;
  };

  return (
    <div>
      {/* Wide screens: one screen, queue and map side by side. Phones: the page scrolls, one view at a time. */}
      <section className="lg:flex lg:h-[calc(100dvh-4rem)] lg:flex-col">
        <SummaryRow />
        <div
          className={cn(
            "relative lg:grid lg:min-h-0 lg:flex-1",
            panelHidden ? "lg:grid-cols-[1fr]" : "lg:grid-cols-[26rem_1fr]",
          )}
        >
          {listShown && (
            <div id="dashboard-panel" className="flex flex-col bg-background lg:min-h-0 lg:border-r">
              <div className="grid gap-3 border-b px-4 pt-4 pb-3">
                <div className="grid gap-1">
                  <div className="flex items-center justify-between gap-2">
                    <h2 className="text-xl">Action queue</h2>
                    {wide && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="rounded-full text-muted-foreground"
                        aria-expanded="true"
                        aria-controls="dashboard-panel"
                        onClick={() => togglePanel(false)}
                      >
                        <PanelLeftClose aria-hidden="true" />
                        Hide panel
                      </Button>
                    )}
                  </div>
                  {query.data !== undefined && (
                    <p className="text-sm">
                      <span className={cn("font-semibold tabular-nums", inspect > 0 && "text-critical")}>
                        {inspect} to inspect before peak.
                      </span>{" "}
                      <span className="text-muted-foreground">Open one to see every reason.</span>
                    </p>
                  )}
                </div>
                {query.data !== undefined && (
                  <>
                    <div className="flex flex-wrap items-center gap-2">
                      <SimulatedLabel show={items.some((i) => i.is_simulated)} />
                      <Freshness fetchedAt={query.dataUpdatedAt} />
                    </div>
                    <Toolbar items={items} filter={filter} setFilter={setFilter} />
                  </>
                )}
              </div>
              <div className="grid content-start px-2 pt-2 pb-6 lg:min-h-0 lg:flex-1 lg:overflow-y-auto lg:pb-4">
                <QueryView
                  {...query}
                  isEmpty={(all) => all.length === 0}
                  emptyMessage="No transformers in this area."
                  onRetry={query.refetch}
                  skeleton={<QueueSkeleton />}
                >
                  {() => (
                    <Queue
                      visible={visible}
                      filtered={filtered}
                      lastOpened={lastOpened}
                      activeId={selectedId ?? hoverId}
                      hrefFor={hrefFor}
                      onHover={setHoverId}
                      onFocusRow={(id) => {
                        setHoverId(id);
                        setFocusId(id);
                      }}
                      onClear={() => setParams({})}
                    />
                  )}
                </QueryView>
              </div>
            </div>
          )}

          {/* The map mounts once data is in, so its first view fits every transformer. */}
          <div
            id="dashboard-map"
            className={cn(
              "relative scroll-mt-16 max-lg:h-[calc(100dvh-4rem)] max-sm:h-[calc(100dvh-8rem-env(safe-area-inset-bottom))]",
              !mapShown && "hidden",
            )}
          >
            {query.data === undefined ? (
              <Skeleton className="h-full rounded-none" />
            ) : (
              <ErrorBoundary
                fallback={
                  <p className="grid h-full place-items-center bg-muted p-6 text-center text-sm text-muted-foreground">
                    Map could not load. The queue has every transformer.
                  </p>
                }
              >
                <Suspense fallback={<Skeleton className="h-full rounded-none" />}>
                  <TransformerMap
                    items={items}
                    shownIds={shownIds}
                    clamps={clamps}
                    clampCounts={counts}
                    clampsAsOf={clampQuery.data?.as_of ?? null}
                    clampsFailed={clampQuery.isError && clampQuery.data === undefined}
                    onRetryClamps={() => void clampQuery.refetch()}
                    activeId={selectedId ?? hoverId ?? focusId}
                    selectedId={selectedId}
                    focusId={focusId}
                    leftInsetPx={0}
                    onHover={setHoverId}
                    onSelect={setSelectedId}
                    onOpen={(id) => {
                      rememberLastOpened(id);
                      navigate(hrefFor(id));
                    }}
                    overlay={overlay}
                    coverageBands={bands}
                    chargers={stations}
                    ringRadiusM={chargers.data?.radius_m ?? 0}
                    legend={legend}
                  />
                </Suspense>
              </ErrorBoundary>
            )}
            {query.data !== undefined && (
              <div className="absolute top-2 left-2 z-10 flex max-w-[calc(100%-4rem)] flex-wrap items-center gap-2">
                {panelHidden && (
                  <Button
                    variant="outline"
                    className="min-h-11 rounded-full bg-card shadow-lg sm:min-h-9"
                    aria-expanded="false"
                    aria-controls="dashboard-panel"
                    onClick={() => togglePanel(true)}
                  >
                    <PanelLeftOpen aria-hidden="true" />
                    Show panel
                  </Button>
                )}
                <OverlayControl value={overlay} onChange={chooseOverlay} />
              </div>
            )}
          </div>

          <Button
            hidden={loadFailed}
            variant="outline"
            className="fixed bottom-4 left-1/2 z-20 min-h-11 -translate-x-1/2 rounded-full bg-card shadow-lg max-sm:bottom-[calc(5rem+env(safe-area-inset-bottom))] lg:hidden"
            onClick={() => {
              const next = phoneView === "list" ? "map" : "list";
              setPhoneView(next);
              // The map fills the screen under the sticky header; the list starts at the top of the page.
              window.requestAnimationFrame(() =>
                next === "map"
                  ? document.getElementById("dashboard-map")?.scrollIntoView?.({ block: "start" })
                  : window.scrollTo?.({ top: 0 }),
              );
            }}
          >
            {phoneView === "list" ? <MapIcon aria-hidden="true" /> : <List aria-hidden="true" />}
            {phoneView === "list" ? "Show map" : "Show list"}
          </Button>
        </div>
      </section>
      <WeatherStrip items={items} />
    </div>
  );
}
