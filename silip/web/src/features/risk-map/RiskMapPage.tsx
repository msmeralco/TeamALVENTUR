import { ChevronDown, List, Map as MapIcon, PanelLeftClose, PanelLeftOpen, Search } from "lucide-react";
import { lazy, Suspense, useEffect, useRef, useState, type ReactNode } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  TIERS,
  filterSearch,
  clampCounts,
  readFilter,
  useClamps,
  useTransformers,
  visibleItems,
  type ListFilter,
  type Tier,
  type TransformerItem,
} from "../../shared/risk";
import { QueryView, SimulatedLabel, TierBadge, cn, formatPct } from "../../shared/ui";
import { Button } from "../../shared/ui/components/button";
import { Card } from "../../shared/ui/components/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "../../shared/ui/components/collapsible";
import { Skeleton } from "../../shared/ui/components/skeleton";
import { ErrorBoundary, Freshness, useDocumentTitle } from "../../shared/ui/feedback";

// MapLibre is large; load it only when the risk map opens.
const TransformerMap = lazy(() => import("./TransformerMap").then((m) => ({ default: m.TransformerMap })));

const WIDE_SCREEN = "(min-width: 64rem)"; // Tailwind `lg`: list and map side by side
// Per tab, so coming back from a card lands on the row you opened.
const LAST_OPENED_KEY = "silip.riskMap.lastOpened";
const SECTION_TITLE: Record<Tier, string> = { Critical: "Needs action", Watch: "Watch", OK: "OK" };
const TIER_DOT: Record<Tier, string> = { Critical: "bg-critical", Watch: "bg-watch", OK: "bg-ok" };

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

interface RowProps {
  item: TransformerItem;
  href: string;
  active: boolean;
  lastOpened: boolean;
  onHover: (id: string | null) => void;
  onFocusRow: (id: string) => void;
}

function TransformerRow({ item, href, active, lastOpened, onHover, onFocusRow }: RowProps) {
  const { risk } = item;
  const moreReasons = risk.reasons.length - 1;
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
        className="block rounded-xl no-underline"
      >
        <Card
          className={cn(
            "gap-2 px-6 py-5 shadow-none transition-shadow duration-150 hover:shadow-lg",
            active && "shadow-lg",
            lastOpened && "ring-2 ring-ring/40",
          )}
        >
          <div className="flex items-center justify-between gap-4">
            <h3 className="text-xl">{item.transformer_id}</h3>
            <span className="flex items-center gap-2">
              {lastOpened && <span className="text-sm text-muted-foreground">Last opened</span>}
              <TierBadge tier={risk.tier} />
            </span>
          </div>
          <p>
            {risk.reasons[0] ?? "No reason given."}
            {moreReasons > 0 && (
              <span className="text-sm whitespace-nowrap text-muted-foreground"> +{moreReasons} more</span>
            )}
          </p>
          <p className="flex flex-wrap gap-x-2 text-sm text-muted-foreground">
            <span>{item.rated_kva} kVA</span>
            <span aria-hidden="true">·</span>
            <span>Confidence {formatPct(risk.confidence)}</span>
            <span aria-hidden="true">·</span>
            <span className="whitespace-nowrap">Coverage {formatPct(risk.coverage_pct)} of homes</span>
          </p>
        </Card>
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

function RiskMapSkeleton() {
  return (
    <div className="grid gap-3">
      {[0, 1, 2, 3].map((i) => (
        <Skeleton key={i} className="h-32 rounded-xl" />
      ))}
    </div>
  );
}

// The list panel over the map on wide screens: 26rem plus its 1rem gap from the edge.
const PANEL_INSET_PX = 432;

/** Tier sections with their rows, or an empty state with Clear filter. */
function TierSections({
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
  return (
    <>
      {TIERS.map((tier) => {
        const rows = visible.filter((i) => i.risk.tier === tier);
        if (rows.length === 0) return null;
        // OK starts folded unless you asked for it, are searching, or came back from one of its rows.
        const open = tier !== "OK" || filtered || rows.some((r) => r.transformer_id === lastOpened);
        return (
          <Collapsible key={`${tier}-${filtered ? "filtered" : "all"}`} defaultOpen={open} asChild>
            <section aria-labelledby={`section-${tier}`} className="grid gap-3">
              <h2 id={`section-${tier}`} className="text-xl">
                <CollapsibleTrigger className="group flex min-h-11 w-full items-center gap-3 rounded-lg text-left">
                  {SECTION_TITLE[tier]}
                  <TierBadge tier={tier} />
                  <span className="font-sans text-sm font-normal text-muted-foreground tabular-nums">
                    {rows.length} {rows.length === 1 ? "transformer" : "transformers"}
                  </span>
                  <ChevronDown
                    aria-hidden="true"
                    className="ml-auto size-5 text-muted-foreground transition-transform duration-150 group-data-[state=open]:rotate-180"
                  />
                </CollapsibleTrigger>
              </h2>
              <CollapsibleContent asChild>
                <ul className="grid gap-3">
                  {rows.map((item) => (
                    <TransformerRow
                      key={item.transformer_id}
                      item={item}
                      href={hrefFor(item.transformer_id)}
                      active={item.transformer_id === activeId}
                      lastOpened={item.transformer_id === lastOpened}
                      onHover={onHover}
                      onFocusRow={onFocusRow}
                    />
                  ))}
                </ul>
              </CollapsibleContent>
            </section>
          </Collapsible>
        );
      })}
    </>
  );
}

/**
 * Engineer risk map, full screen: the map fills the page and the ranked list sits in a panel over it
 * (beside it on wide screens, swapped with a toggle on phones). Critical first in the list.
 */
export function RiskMapPage() {
  useDocumentTitle("Risk map");
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const filter = readFilter(params);
  const query = useTransformers();
  const clampQuery = useClamps();
  const wide = useMediaQuery(WIDE_SCREEN);
  const [hoverId, setHoverId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [focusId, setFocusId] = useState<string | null>(null);
  // Phones show one at a time; the map leads. Wide screens show both, and the panel can be hidden.
  const [phoneView, setPhoneView] = useState<"list" | "map">("map");
  const [panelOpen, setPanelOpen] = useState(true);
  const [lastOpened] = useState(readLastOpened);
  const restored = useRef(false);
  // A failed first load has nothing to map, so the panel shows its error and retry on every screen.
  const loadFailed = query.data === undefined && !query.isPending;
  const listShown = loadFailed || (wide ? panelOpen : phoneView === "list");
  const leftInsetPx = wide && panelOpen ? PANEL_INSET_PX : 0;

  const setFilter = (next: Partial<ListFilter>, replace = false) => {
    setParams(new URLSearchParams(filterSearch({ ...filter, ...next })), { replace });
  };
  const hrefFor = (id: string) => `/engineer/transformers/${encodeURIComponent(id)}${filterSearch(filter)}`;

  // Back from a card: bring the row you opened into view once (in the panel's own scroll).
  useEffect(() => {
    if (restored.current || query.data === undefined || lastOpened === null || !listShown) return;
    restored.current = true;
    document.getElementById(`row-${lastOpened}`)?.scrollIntoView?.({ block: "center" });
  }, [query.data, lastOpened, listShown]);

  // A pin tapped on the map: show its row in the panel too.
  useEffect(() => {
    if (selectedId !== null && wide && panelOpen) {
      document.getElementById(`row-${selectedId}`)?.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
    }
  }, [selectedId, wide, panelOpen]);

  const items = query.data ?? [];
  const visible = visibleItems(items, filter);
  const filtered = filter.tier !== null || filter.query.trim() !== "";
  const shownIds = new Set(visible.map((i) => i.transformer_id));
  const critical = items.filter((i) => i.risk.tier === "Critical").length;
  const clamps = clampQuery.data?.clamps ?? [];
  const counts = clampCounts(clamps);

  return (
    <section className="relative h-[calc(100dvh-4rem)] overflow-hidden max-sm:h-[calc(100dvh-8rem-env(safe-area-inset-bottom))]">
      {/* The map is the page. It mounts once data is in, so its first view fits every transformer. */}
      <div className="absolute inset-0">
        {query.data === undefined ? (
          <Skeleton className="h-full rounded-none" />
        ) : (
          <ErrorBoundary
            fallback={
              <p className="grid h-full place-items-center bg-muted p-6 text-center text-sm text-muted-foreground">
                Map could not load. The list has every transformer.
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
                activeId={selectedId ?? hoverId}
                selectedId={selectedId}
                focusId={focusId}
                leftInsetPx={leftInsetPx}
                onHover={setHoverId}
                onSelect={setSelectedId}
                onOpen={(id) => {
                  rememberLastOpened(id);
                  navigate(hrefFor(id));
                }}
              />
            </Suspense>
          </ErrorBoundary>
        )}
      </div>

      {listShown ? (
        <div
          className={cn(
            "absolute z-10 flex flex-col bg-background",
            "max-lg:inset-0",
            "lg:top-4 lg:bottom-4 lg:left-4 lg:w-[26rem] lg:rounded-xl lg:border lg:shadow-lg",
          )}
        >
          <div className="grid gap-3 border-b px-4 pt-4 pb-3">
            <div className="flex items-start gap-2">
              <div className="grid gap-1">
                <h1 className="text-xl">Transformer risk, next 24 h</h1>
                <p className="text-sm text-muted-foreground">Critical first. Open a transformer to see every reason.</p>
              </div>
              <Button
                variant="ghost"
                className="ml-auto min-h-11 shrink-0 rounded-full max-lg:hidden sm:min-h-9"
                onClick={() => setPanelOpen(false)}
              >
                <PanelLeftClose aria-hidden="true" />
                Hide list
              </Button>
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
          <div className="grid min-h-0 flex-1 content-start gap-6 overflow-y-auto px-4 pt-4 pb-24 lg:pb-4">
            <QueryView
              {...query}
              isEmpty={(all) => all.length === 0}
              emptyMessage="No transformers in this area."
              onRetry={query.refetch}
              skeleton={<RiskMapSkeleton />}
            >
              {() => (
                <TierSections
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
      ) : (
        query.data !== undefined && (
          // Map view: the one-line summary stays visible over the map, with the label the data needs.
          <div className="absolute top-2 left-2 z-10 flex max-w-[calc(100%-4.5rem)] flex-wrap items-center gap-2 rounded-xl border bg-card/95 p-2 shadow-lg">
            <h1 className="px-1 text-base font-bold">Transformer risk</h1>
            {critical > 0 && <TierBadge tier="Critical" />}
            <span className="text-sm tabular-nums">
              {critical} need{critical === 1 ? "s" : ""} action
            </span>
            <SimulatedLabel show={items.some((i) => i.is_simulated)} />
            {wide && (
              <Button variant="outline" className="min-h-9 rounded-full" onClick={() => setPanelOpen(true)}>
                <PanelLeftOpen aria-hidden="true" />
                Show list
              </Button>
            )}
          </div>
        )
      )}

      <Button
        hidden={loadFailed}
        variant="outline"
        className="absolute bottom-4 left-1/2 z-20 min-h-11 -translate-x-1/2 rounded-full shadow-lg lg:hidden"
        onClick={() => setPhoneView(phoneView === "list" ? "map" : "list")}
      >
        {phoneView === "list" ? <MapIcon aria-hidden="true" /> : <List aria-hidden="true" />}
        {phoneView === "list" ? "Show map" : "Show list"}
      </Button>
    </section>
  );
}
