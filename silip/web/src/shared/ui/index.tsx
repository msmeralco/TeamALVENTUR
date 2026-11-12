import type { ReactNode } from "react";
import { toast } from "sonner";
import { ApiError } from "../api/client";
import { Badge } from "./components/badge";
import { Button } from "./components/button";
import { Card } from "./components/card";
import { Skeleton } from "./components/skeleton";
import { cn } from "./cn";

export { cn };

type Tier = "OK" | "Watch" | "Critical";
const TIER_CLASS: Record<Tier, string> = {
  OK: "bg-ok-soft text-ok",
  Watch: "bg-watch-soft text-watch",
  Critical: "bg-critical-soft text-critical",
};

/** Status is always color plus word, never color alone. */
export function TierBadge({ tier }: { tier: Tier }) {
  return (
    <Badge className={cn("gap-1.5 px-2.5 font-semibold", TIER_CLASS[tier])}>
      <span aria-hidden="true" className="size-2 rounded-full bg-current" />
      {tier}
    </Badge>
  );
}

/** Required wherever data has is_simulated = true. */
export function SimulatedLabel({ show }: { show: boolean }) {
  return show ? (
    <Badge variant="secondary" className="px-2.5 font-semibold text-muted-foreground">
      Simulated data
    </Badge>
  ) : null;
}

/** Page title, an optional one-line lede and an optional row of labels. */
export function PageHead({
  title,
  lede,
  children,
  className,
}: {
  title: ReactNode;
  lede?: ReactNode;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <header className={cn("mb-6 grid gap-2", className)}>
      <h1 className="text-3xl tracking-tight text-balance">{title}</h1>
      {lede !== undefined && <p className="text-sm text-muted-foreground">{lede}</p>}
      {children}
    </header>
  );
}

/** A centered message card for sign-in, no-access and not-found states. */
export function StateCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card className="mx-auto mt-10 max-w-md items-center gap-3 px-6 py-10 text-center">
      <h1 className="text-xl">{title}</h1>
      {children}
    </Card>
  );
}

interface QueryViewProps<T> {
  isPending: boolean;
  isFetching: boolean;
  error: Error | null;
  data: T | undefined;
  isEmpty: (data: T) => boolean;
  emptyMessage: ReactNode;
  onRetry: () => Promise<{ isSuccess: boolean }>;
  /** A placeholder shaped like the loaded page, so nothing jumps when data arrives. */
  skeleton?: ReactNode;
  children: (data: T) => ReactNode;
}

async function retry(onRetry: QueryViewProps<unknown>["onRetry"]) {
  const result = await onRetry();
  if (result.isSuccess) toast.success("Loaded. Thanks for trying again.");
}

/** Loading, error (with retry) and empty states for every data view. */
export function QueryView<T>({
  isPending,
  isFetching,
  error,
  data,
  isEmpty,
  emptyMessage,
  onRetry,
  skeleton,
  children,
}: QueryViewProps<T>) {
  if (isPending && !isFetching && error === null) {
    // Paused (offline before the first load): say so instead of showing a skeleton forever.
    return <Card className="px-6 py-8">You are offline. This view loads when you reconnect.</Card>;
  }
  if (isPending && error === null) {
    return (
      <div aria-busy="true">
        <span className="sr-only">Loading…</span>
        {skeleton ?? (
          <div className="grid gap-4">
            <Skeleton className="h-24 rounded-xl" />
            <Skeleton className="h-24 rounded-xl" />
            <Skeleton className="h-24 rounded-xl" />
          </div>
        )}
      </div>
    );
  }
  // A failed background refresh keeps the last data on screen; the error card is for a first load.
  if (data === undefined) {
    return (
      <Card role="alert" className="max-w-2xl items-start gap-2 px-6 py-8">
        <h2 className="text-xl">Could not load this view</h2>
        <p className="text-sm text-muted-foreground">
          {error instanceof ApiError
            ? error.message
            : "Could not reach the server. Check your connection and try again."}
        </p>
        <Button
          variant="outline"
          className="mt-2 rounded-full"
          disabled={isFetching}
          onClick={() => void retry(onRetry)}
        >
          {isFetching ? "Trying again…" : "Try again"}
        </Button>
      </Card>
    );
  }
  if (isEmpty(data)) {
    return <Card className="max-w-2xl px-6 py-8">{emptyMessage}</Card>;
  }
  return <>{children(data)}</>;
}

export function formatMinutes(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const rest = Math.round(minutes % 60);
  if (hours === 0) return `${rest} min`;
  return rest === 0 ? `${hours} h` : `${hours} h ${rest} min`;
}

/** Day and time, e.g. "Fri 11:45 PM". */
export function formatWhen(date: Date): string {
  return date.toLocaleString([], { weekday: "short", hour: "numeric", minute: "2-digit" });
}

export function formatPct(fraction: number): string {
  return `${Math.round(fraction * 100)}%`;
}

export function formatClock(date: Date): string {
  return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}
