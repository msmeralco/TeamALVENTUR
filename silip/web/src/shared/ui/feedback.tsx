import { WifiOff } from "lucide-react";
import { Component, useEffect, useState, type ReactNode } from "react";
import { Button } from "./components/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "./components/tooltip";
import { StateCard } from "./index";

const MS_PER_MIN = 60_000;
const RELATIVE_TICK_MS = 30_000;
// Data older than this gets a muted note. [VERIFY] with engineers how stale is too stale for a 24 h forecast.
export const STALE_AFTER_MS = 2 * 60 * MS_PER_MIN;

/** "just now", "3 min ago", "2 h ago", "5 days ago". */
export function relativeTime(then: number, now: number): string {
  const minutes = Math.max(0, Math.floor((now - then) / MS_PER_MIN));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 48) return `${hours} h ago`;
  return `${Math.floor(hours / 24)} days ago`;
}

function useNow(): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), RELATIVE_TICK_MS);
    return () => window.clearInterval(id);
  }, []);
  return now;
}

const absolute = (ms: number) =>
  new Date(ms).toLocaleString([], {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });

/**
 * "Updated 3 min ago" for when this page last got data, with the exact time in a tooltip.
 * `dataAsOf` is when the data itself was measured; if it is old, a muted note says so.
 */
export function Freshness({ fetchedAt, dataAsOf }: { fetchedAt: number; dataAsOf?: string }) {
  const now = useNow();
  const asOfMs = dataAsOf === undefined ? null : new Date(dataAsOf).getTime();
  const stale = asOfMs !== null && now - asOfMs > STALE_AFTER_MS;
  return (
    <span className="inline-flex flex-wrap items-center gap-x-2 text-sm text-muted-foreground">
      <Tooltip>
        <TooltipTrigger asChild>
          <span tabIndex={0} className="rounded-sm underline decoration-dotted underline-offset-4">
            <span aria-hidden="true">Updated {relativeTime(fetchedAt, now)}</span>
            <span className="sr-only">Updated {absolute(fetchedAt)}</span>
          </span>
        </TooltipTrigger>
        <TooltipContent>{absolute(fetchedAt)}</TooltipContent>
      </Tooltip>
      {/* Announces each refresh once, not every minute the relative time ticks. */}
      <span aria-live="polite" className="sr-only">
        Data updated at {absolute(fetchedAt)}
      </span>
      {stale && asOfMs !== null && <span>Data may be out of date (measured {absolute(asOfMs)}).</span>}
    </span>
  );
}

export function useOnline(): boolean {
  const [online, setOnline] = useState(() => navigator.onLine);
  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);
  return online;
}

/** A slim notice under the header. The page keeps the last data it loaded. */
export function OfflineBanner() {
  const online = useOnline();
  if (online) return null;
  return (
    <div role="status" className="border-b bg-muted">
      <p className="mx-auto flex max-w-6xl items-center gap-2 px-4 py-2 text-sm sm:px-6">
        <WifiOff aria-hidden="true" className="size-4 shrink-0" />
        You are offline. This page shows the last data it loaded.
      </p>
    </div>
  );
}

/** "T-106 · Dashboard · SILIP". */
export function useDocumentTitle(...parts: string[]) {
  const title = [...parts, "SILIP"].join(" · ");
  useEffect(() => {
    document.title = title;
  }, [title]);
}

/** Shows `fallback` instead of crashing when a child throws (a render error or a lazy chunk that failed to load). */
export class ErrorBoundary extends Component<{ fallback: ReactNode; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error: unknown) {
    console.error("View crashed", error);
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

/** Catches errors in one route so the header and nav still work. Reset by changing `key`. */
export function RouteErrorBoundary({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary
      fallback={
        <StateCard
          role="alert"
          title="This page stopped working"
          actions={
            <Button className="min-h-11 rounded-full" onClick={() => window.location.reload()}>
              Reload
            </Button>
          }
        >
          <p className="text-sm text-muted-foreground">Reloading usually fixes it. Your sign-in is kept.</p>
        </StateCard>
      }
    >
      {children}
    </ErrorBoundary>
  );
}
