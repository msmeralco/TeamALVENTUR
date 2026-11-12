import { useState, type KeyboardEvent, type PointerEvent } from "react";
import type { Schemas } from "../../shared/api/client";
import type { PeakMark } from "../../shared/ui/HeatIndexChart";
import { cn, formatWhen } from "../../shared/ui";
import { HEAT_BANDS, forecastDays, heatCategory, rainGlyph } from "./heat";

type Hour = Schemas["AreaHour"];

const WIDTH = 600;
const HEIGHT = 100;
const RAIN_HEIGHT = 24;
const HOUR_MS = 3_600_000;
const THIN = "[vector-effect:non-scaling-stroke]";
// A band label needs this much of the plot height to fit without crowding.
const MIN_LABEL_SHARE = 0.16;

const hourKey = (ms: number) => Math.floor(ms / HOUR_MS);
const pct = (v: number, of: number) => `${(100 * v) / of}%`;
const fmtC = (c: number | null) => (c === null ? "No value" : `${c.toFixed(1)} °C`);

/**
 * 48 h heat index on one °C scale over faint NOAA bands, a now marker and the Critical peaks.
 * Rain, when any, sits in its own small row with its own scale. Day columns carry a rain glyph.
 */
export function WeatherChart({ hours, marks, nowMs }: { hours: Hour[]; marks: PeakMark[]; nowMs: number }) {
  const [hover, setHover] = useState<number | null>(null);
  const times = hours.map((h) => new Date(h.ts).getTime());
  const start = times[0];
  const end = times[times.length - 1];
  const span = Math.max(end - start, 1);
  const values = hours.flatMap((h) => (h.heat_index_max_c === null ? [] : [h.heat_index_max_c]));
  const lo = Math.floor(Math.min(...values) - 1);
  const hi = Math.ceil(Math.max(...values) + 1);
  const x = (ms: number) => (WIDTH * (ms - start)) / span;
  const y = (c: number) => HEIGHT * (1 - (c - lo) / Math.max(hi - lo, 1));
  const rainMax = Math.max(0, ...hours.map((h) => h.precipitation_max_mm ?? 0));
  const showRain = rainMax > 0;
  const barWidth = (0.6 * WIDTH * HOUR_MS) / span;
  const nowShown = nowMs >= start && nowMs <= end;

  const path = hours
    .map((h, i) =>
      h.heat_index_max_c === null
        ? ""
        : `${i === 0 || hours[i - 1].heat_index_max_c === null ? "M" : "L"}${x(times[i]).toFixed(1)},${y(h.heat_index_max_c).toFixed(1)}`,
    )
    .join(" ");

  const bands = HEAT_BANDS.flatMap((b) => {
    if (b.from >= hi || b.to <= lo) return [];
    const top = y(Math.min(b.to, hi));
    const bottom = y(Math.max(b.from, lo));
    return [{ ...b, top, height: bottom - top }];
  });

  const marksByHour = new Map<number, string[]>();
  for (const mark of marks) {
    const ms = new Date(mark.ts).getTime();
    if (ms < start || ms > end) continue;
    marksByHour.set(hourKey(ms), [...(marksByHour.get(hourKey(ms)) ?? []), ...mark.ids]);
  }
  const markHours = [...marksByHour.entries()].map(([key, ids]) => {
    const index = times.findIndex((t) => hourKey(t) === key);
    return { key, ms: key * HOUR_MS, ids, heat: index === -1 ? null : hours[index].heat_index_max_c };
  });
  const markedCount = markHours.reduce((sum, m) => sum + m.ids.length, 0);

  const onMove = (event: PointerEvent<HTMLDivElement>) => {
    const box = event.currentTarget.getBoundingClientRect();
    const ms = start + ((event.clientX - box.left) / box.width) * span;
    let best = 0;
    times.forEach((t, i) => {
      if (Math.abs(t - ms) < Math.abs(times[best] - ms)) best = i;
    });
    setHover(best);
  };
  const onKey = (event: KeyboardEvent<HTMLDivElement>) => {
    const last = hours.length - 1;
    const from = hover ?? 0;
    const moves: Record<string, number> = { ArrowLeft: from - 1, ArrowRight: from + 1, Home: 0, End: last };
    const target = moves[event.key];
    if (target === undefined) return;
    event.preventDefault();
    setHover(Math.min(last, Math.max(0, target)));
  };
  const hovered = hover === null ? undefined : hours[hover];
  const hoveredIds = hover === null ? [] : (marksByHour.get(hourKey(times[hover])) ?? []);

  return (
    <figure className="m-0 grid gap-2">
      <figcaption className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-muted-foreground">
        <span className="inline-flex items-center gap-2">
          <span aria-hidden="true" className="w-5 border-t-2 border-brand" />
          Heat index, °C
        </span>
        {markedCount > 0 && (
          <span className="inline-flex items-center gap-2">
            <span aria-hidden="true" className="size-2.5 rounded-full bg-critical ring-2 ring-card" />
            Critical transformer peak ({markedCount})
          </span>
        )}
        {showRain && (
          <span className="inline-flex items-center gap-2">
            <span aria-hidden="true" className="h-2.5 w-1.5 rounded-t-sm bg-muted-foreground" />
            Rain, mm per hour
          </span>
        )}
      </figcaption>
      <div
        role="img"
        tabIndex={0}
        aria-label={`Heat index by hour, ${values.length} hours, shaded by NOAA heat index band${markedCount > 0 ? `, ${markedCount} Critical transformer peaks marked` : ""}. Use the arrow keys to read values, or open the table below.`}
        className="relative ml-11 grid touch-pan-y gap-1 rounded-sm"
        onPointerMove={onMove}
        onPointerLeave={() => setHover(null)}
        onKeyDown={onKey}
        onBlur={() => setHover(null)}
      >
        <div className="relative h-32">
          {bands.map((b) => (
            <div
              key={b.label}
              aria-hidden="true"
              className={cn("absolute inset-x-0", b.tint)}
              style={{ top: pct(b.top, HEIGHT), height: pct(b.height, HEIGHT) }}
            >
              {b.height / HEIGHT >= MIN_LABEL_SHARE && (
                <span className="absolute top-0.5 right-1 text-xs leading-tight text-muted-foreground">{b.label}</span>
              )}
            </div>
          ))}
          {[lo, hi].map((tick) => (
            <span
              key={tick}
              className="absolute right-[calc(100%+0.5rem)] -translate-y-1/2 text-sm leading-none text-muted-foreground tabular-nums"
              style={{ top: pct(y(tick), HEIGHT) }}
            >
              {tick}°
            </span>
          ))}
          <svg
            aria-hidden="true"
            viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
            preserveAspectRatio="none"
            className="absolute inset-0 block h-full w-full overflow-visible"
          >
            {markHours.map((m) => (
              <line key={m.key} className={`stroke-critical ${THIN}`} x1={x(m.ms)} x2={x(m.ms)} y1={0} y2={HEIGHT} />
            ))}
            {nowShown && (
              <line
                className={`stroke-foreground ${THIN}`}
                strokeDasharray="3 3"
                x1={x(nowMs)}
                x2={x(nowMs)}
                y1={0}
                y2={HEIGHT}
              />
            )}
            <path className={`fill-none stroke-brand stroke-2 ${THIN}`} d={path} />
            {hover !== null && (
              <line
                className={`stroke-muted-foreground ${THIN}`}
                x1={x(times[hover])}
                x2={x(times[hover])}
                y1={0}
                y2={HEIGHT}
              />
            )}
          </svg>
          {nowShown && (
            <span
              className="pointer-events-none absolute top-0 -translate-x-1/2 -translate-y-full rounded-full bg-card px-1.5 text-xs font-semibold"
              style={{ left: pct(x(nowMs), WIDTH) }}
            >
              Now
            </span>
          )}
          {markHours.map(
            (m) =>
              m.heat !== null && (
                <span
                  key={m.key}
                  title={`Critical peak: ${m.ids.join(", ")}`}
                  className="absolute size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-critical ring-2 ring-card"
                  style={{ left: pct(x(m.ms), WIDTH), top: pct(y(m.heat), HEIGHT) }}
                />
              ),
          )}
          {hovered !== undefined && hover !== null && (
            <div
              aria-live="polite"
              className={cn(
                "pointer-events-none absolute top-0 z-10 grid rounded-lg border bg-popover px-3 py-2 text-sm whitespace-nowrap shadow-lg",
                x(times[hover]) > WIDTH / 2 ? "-translate-x-[calc(100%+0.5rem)]" : "translate-x-2",
              )}
              style={{ left: pct(x(times[hover]), WIDTH) }}
            >
              <span className="text-muted-foreground">{formatWhen(new Date(hovered.ts))}</span>
              <span>
                <strong>Heat index {fmtC(hovered.heat_index_max_c)}</strong>
                {hovered.heat_index_max_c !== null && ` · ${heatCategory(hovered.heat_index_max_c)}`}
              </span>
              <span>Temperature {fmtC(hovered.temperature_max_c)}</span>
              <span>Rain {(hovered.precipitation_max_mm ?? 0).toFixed(1)} mm</span>
              {hoveredIds.length > 0 && (
                <span>
                  Critical peak: {hoveredIds.slice(0, 4).join(", ")}
                  {hoveredIds.length > 4 && ` +${hoveredIds.length - 4} more`}
                </span>
              )}
            </div>
          )}
        </div>
        {showRain && (
          <svg
            aria-hidden="true"
            viewBox={`0 0 ${WIDTH} ${RAIN_HEIGHT}`}
            preserveAspectRatio="none"
            className="block h-6 w-full border-b"
          >
            {hours.map((h, i) =>
              (h.precipitation_max_mm ?? 0) > 0 ? (
                <rect
                  key={h.ts}
                  className="fill-muted-foreground"
                  x={x(times[i]) - barWidth / 2}
                  width={barWidth}
                  y={RAIN_HEIGHT * (1 - (h.precipitation_max_mm ?? 0) / rainMax)}
                  height={(RAIN_HEIGHT * (h.precipitation_max_mm ?? 0)) / rainMax}
                />
              ) : null,
            )}
          </svg>
        )}
      </div>
      <div className="relative ml-11 h-10 text-sm text-muted-foreground">
        {forecastDays(hours).map((d) => {
          const { Icon, label } = rainGlyph(d.maxRain);
          const center = x((d.startMs + d.endMs) / 2);
          return (
            <span
              key={d.startMs}
              title={`${label}, wettest hour ${d.maxRain.toFixed(1)} mm`}
              className="absolute top-0 grid -translate-x-1/2 justify-items-center"
              style={{ left: pct(Math.min(Math.max(center, 30), WIDTH - 30), WIDTH) }}
            >
              <Icon aria-hidden="true" className="size-4" />
              <span className="text-xs whitespace-nowrap">
                {new Date(d.startMs).toLocaleDateString([], { weekday: "short" })}
                <span className="sr-only">, {label}</span>
              </span>
            </span>
          );
        })}
      </div>
      <details>
        <summary className="flex min-h-11 cursor-pointer items-center text-sm text-muted-foreground sm:min-h-0">
          Show hourly values as a table
        </summary>
        <table className="mt-2 w-full text-sm tabular-nums">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="py-1 font-semibold">Time</th>
              <th className="py-1 text-right font-semibold">Heat index</th>
              <th className="py-1 text-right font-semibold">Temp</th>
              <th className="py-1 text-right font-semibold">Rain</th>
            </tr>
          </thead>
          <tbody>
            {hours.map((h, i) => (
              <tr key={h.ts} className="border-b">
                <td className="py-1">
                  {formatWhen(new Date(h.ts))}
                  {marksByHour.has(hourKey(times[i])) &&
                    `, Critical peak: ${marksByHour.get(hourKey(times[i]))?.join(", ")}`}
                </td>
                <td className="py-1 text-right">
                  {fmtC(h.heat_index_max_c)}
                  {h.heat_index_max_c !== null && `, ${heatCategory(h.heat_index_max_c)}`}
                </td>
                <td className="py-1 text-right">{fmtC(h.temperature_max_c)}</td>
                <td className="py-1 text-right">{(h.precipitation_max_mm ?? 0).toFixed(1)} mm</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
