import { useQuery } from "@tanstack/react-query";
import { REFRESH_INTERVAL_MS, api, unwrap } from "../../shared/api/client";

// Chargers are a delivered list that changes rarely; no need to poll.
const CHARGERS_STALE_MS = 60 * 60_000;

export function useSummary() {
  return useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: async () => unwrap(await api.GET("/api/v1/dashboard/summary")),
    refetchInterval: REFRESH_INTERVAL_MS,
  });
}

export function useOutlook() {
  return useQuery({
    queryKey: ["weather", "outlook"],
    queryFn: async () => unwrap(await api.GET("/api/v1/weather/outlook")),
    refetchInterval: REFRESH_INTERVAL_MS,
  });
}

export function useCoverage() {
  return useQuery({
    queryKey: ["clamps", "coverage"],
    queryFn: async () => unwrap(await api.GET("/api/v1/clamps/coverage")),
    refetchInterval: REFRESH_INTERVAL_MS,
  });
}

/** Only fetched once the EV overlay is first opened. */
export function useChargers(enabled: boolean) {
  return useQuery({
    queryKey: ["ev", "chargers"],
    queryFn: async () => unwrap(await api.GET("/api/v1/ev/chargers")),
    enabled,
    staleTime: CHARGERS_STALE_MS,
  });
}
