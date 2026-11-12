import type { ReactNode } from "react";

type Tier = "OK" | "Watch" | "Critical";
const TIER_COLOR: Record<Tier, string> = { OK: "var(--ok)", Watch: "var(--watch)", Critical: "var(--critical)" };

/** Status is always color plus word, never color alone. */
export function TierBadge({ tier }: { tier: Tier }) {
  return <strong style={{ color: TIER_COLOR[tier] }}>{tier}</strong>;
}

/** Required wherever data has is_simulated = true. */
export function SimulatedLabel({ show }: { show: boolean }) {
  return show ? <p className="muted">Simulated data</p> : null;
}

interface QueryViewProps<T> {
  isPending: boolean;
  error: Error | null;
  data: T | undefined;
  isEmpty: (data: T) => boolean;
  emptyMessage: string;
  onRetry: () => void;
  children: (data: T) => ReactNode;
}

/** Loading, error (with retry) and empty states for every data view. */
export function QueryView<T>({ isPending, error, data, isEmpty, emptyMessage, onRetry, children }: QueryViewProps<T>) {
  if (isPending) return <p className="muted">Loading…</p>;
  if (error !== null || data === undefined) {
    return (
      <p role="alert">
        Could not load this view. {error?.message} <button onClick={onRetry}>Try again</button>
      </p>
    );
  }
  if (isEmpty(data)) return <p className="muted">{emptyMessage}</p>;
  return <>{children(data)}</>;
}

export function formatMinutes(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const rest = Math.round(minutes % 60);
  return hours > 0 ? `${hours} h ${rest} min` : `${rest} min`;
}
