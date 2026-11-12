import { CloudLightning, CloudRain, CloudSun, Sun, type LucideIcon } from "lucide-react";
import type { Schemas } from "../../shared/api/client";

type Hour = Schemas["AreaHour"];

/**
 * NOAA heat index chart bands, converted from °F (80, 90, 103, 125) to °C.
 * Source: NOAA National Weather Service heat index chart.
 */
export const HEAT_BANDS = [
  { from: 27, to: 32, label: "Caution", tint: "bg-muted/60" },
  { from: 32, to: 41, label: "Extreme caution", tint: "bg-watch-soft/50" },
  { from: 41, to: 54, label: "Danger", tint: "bg-watch-soft" },
  { from: 54, to: Infinity, label: "Extreme danger", tint: "bg-watch/20" },
] as const;

export const HEAT_SOURCE = "Heat index bands: NOAA National Weather Service";

/** NOAA word for a heat index in °C. */
export function heatCategory(c: number): string {
  for (let i = HEAT_BANDS.length - 1; i >= 0; i--) if (c >= HEAT_BANDS[i].from) return HEAT_BANDS[i].label;
  return "Below caution";
}

/** Danger and up take the Watch color; lower bands stay neutral. */
export const isHeatWarning = (c: number) => c >= HEAT_BANDS[2].from;

/** The forecast hour holding `nowMs`, else the first hour (the forecast starts later or ended). */
export function currentHour(hours: Hour[], nowMs: number): Hour | undefined {
  const past = hours.filter((h) => new Date(h.ts).getTime() <= nowMs);
  return past[past.length - 1] ?? hours[0];
}

/** Hottest hour by heat index, or undefined when no hour has a value. */
export function peakHour(hours: Hour[]): Hour | undefined {
  return hours.reduce<Hour | undefined>(
    (best, h) =>
      h.heat_index_max_c !== null && (best === undefined || h.heat_index_max_c > (best.heat_index_max_c ?? -Infinity))
        ? h
        : best,
    undefined,
  );
}

const dayKey = (d: Date) => `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;

/** "2 PM today", "2 PM tomorrow" or "2 PM Fri". */
export function relativeWhen(iso: string, nowMs: number): string {
  const date = new Date(iso);
  const time = date.toLocaleTimeString([], { hour: "numeric" });
  const today = new Date(nowMs);
  const tomorrow = new Date(nowMs + 86_400_000);
  if (dayKey(date) === dayKey(today)) return `${time} today`;
  if (dayKey(date) === dayKey(tomorrow)) return `${time} tomorrow`;
  return `${time} ${date.toLocaleDateString([], { weekday: "short" })}`;
}

/** A day's glyph and word from its wettest hour, on PAGASA rainfall intensity steps (mm/h). [VERIFY] */
export function rainGlyph(maxMmPerHour: number): { Icon: LucideIcon; label: string } {
  if (maxMmPerHour < 0.1) return { Icon: Sun, label: "Dry" };
  if (maxMmPerHour < 2.5) return { Icon: CloudSun, label: "Light rain" };
  if (maxMmPerHour < 7.5) return { Icon: CloudRain, label: "Moderate rain" };
  return { Icon: CloudLightning, label: "Heavy rain" };
}

/** Local calendar days in the forecast, each with its first and last hour and wettest hour. */
export function forecastDays(hours: Hour[]): { startMs: number; endMs: number; maxRain: number }[] {
  const days: { key: string; startMs: number; endMs: number; maxRain: number }[] = [];
  for (const h of hours) {
    const ms = new Date(h.ts).getTime();
    const key = dayKey(new Date(ms));
    const last = days[days.length - 1];
    if (last?.key === key) {
      last.endMs = ms;
      last.maxRain = Math.max(last.maxRain, h.precipitation_max_mm ?? 0);
    } else {
      days.push({ key, startMs: ms, endMs: ms, maxRain: h.precipitation_max_mm ?? 0 });
    }
  }
  return days;
}
