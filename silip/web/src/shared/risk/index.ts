import { useQuery } from "@tanstack/react-query";
import { REFRESH_INTERVAL_MS, api, unwrap, type Schemas } from "../api/client";

/**
 * The engineer risk list: one query, one order and one filter, shared by the risk map
 * and the transformer card (for Previous / Next), so both agree on what "next" means.
 */
export type TransformerItem = Schemas["TransformerRisk"];
export type Tier = TransformerItem["risk"]["tier"];

export const TIERS: Tier[] = ["Critical", "Watch", "OK"];
const TIER_RANK: Record<Tier, number> = { Critical: 0, Watch: 1, OK: 2 };

export function useTransformers() {
  return useQuery({
    queryKey: ["transformers"],
    queryFn: async () => unwrap(await api.GET("/api/v1/transformers")),
    refetchInterval: REFRESH_INTERVAL_MS,
  });
}

/** Critical first; within a tier, the highest forecast peak first. */
export function byUrgency(a: TransformerItem, b: TransformerItem): number {
  return TIER_RANK[a.risk.tier] - TIER_RANK[b.risk.tier] || b.risk.peak_load_pct - a.risk.peak_load_pct;
}

/** "T-106", "t106", "t 106" and "106" all become "106"; other text is kept, upper-cased. */
export function normalizeId(text: string): string {
  return text
    .toUpperCase()
    .replace(/[\s-]+/g, "")
    .replace(/^T(?=\d|$)/, "");
}

/** True if `query` is empty or part of the transformer ID, ignoring case, spaces, dashes and the "T". */
export function matchesId(transformerId: string, query: string): boolean {
  const wanted = normalizeId(query);
  return wanted === "" || normalizeId(transformerId).includes(wanted);
}

export interface ListFilter {
  tier: Tier | null;
  query: string;
}

/** Reads `?tier=Critical&q=106`; unknown tiers are ignored. */
export function readFilter(params: URLSearchParams): ListFilter {
  const tier = params.get("tier");
  return {
    tier: TIERS.find((t) => t === tier) ?? null,
    query: params.get("q") ?? "",
  };
}

/** The same filter as URL params ("" when nothing is filtered), to carry it between pages. */
export function filterSearch(filter: ListFilter): string {
  const params = new URLSearchParams();
  if (filter.tier !== null) params.set("tier", filter.tier);
  if (filter.query.trim() !== "") params.set("q", filter.query.trim());
  const text = params.toString();
  return text === "" ? "" : `?${text}`;
}

/** The list in urgency order, narrowed by tier and ID search. */
export function visibleItems(items: TransformerItem[], filter: ListFilter): TransformerItem[] {
  return items
    .filter((i) => (filter.tier === null || i.risk.tier === filter.tier) && matchesId(i.transformer_id, filter.query))
    .sort(byUrgency);
}

export type ClampPoint = Schemas["ClampPoint"];

/** Clamp devices for the map and the card. Device facts only; the API never sends usage here. */
export function useClamps() {
  return useQuery({
    queryKey: ["clamps"],
    queryFn: async () => unwrap(await api.GET("/api/v1/clamps")),
    refetchInterval: REFRESH_INTERVAL_MS,
  });
}

export interface ClampCount {
  total: number;
  online: number;
}

/** Installed and online clamps per transformer. */
export function clampCounts(clamps: ClampPoint[]): Map<string, ClampCount> {
  const counts = new Map<string, ClampCount>();
  for (const clamp of clamps) {
    const count = counts.get(clamp.transformer_id) ?? { total: 0, online: 0 };
    count.total += 1;
    if (clamp.status === "online") count.online += 1;
    counts.set(clamp.transformer_id, count);
  }
  return counts;
}

const MS_PER_MIN = 60_000;

/** "12 min before data time": judged on the data's clock, not the viewer's, so simulated days read right. */
export function reportAge(lastSeenAt: string | null, asOf: string | null): string {
  if (lastSeenAt === null) return "No report yet";
  if (asOf === null) return "Last report time unknown";
  const minutes = Math.max(0, Math.round((new Date(asOf).getTime() - new Date(lastSeenAt).getTime()) / MS_PER_MIN));
  if (minutes < 1) return "Last report at data time";
  if (minutes < 60) return `Last report ${minutes} min before data time`;
  const hours = Math.floor(minutes / 60);
  if (hours < 48) return `Last report ${hours} h before data time`;
  return `Last report ${Math.floor(hours / 24)} days before data time`;
}
