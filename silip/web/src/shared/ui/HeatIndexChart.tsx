import { useState, type KeyboardEvent, type PointerEvent } from "react";
import { cn, formatWhen } from "./index";

export interface HeatHour {
  ts: string;
  heatC: number | null;
  rainMm: number | null;
}

/** A forecast peak to mark on the time axis, e.g. a Critical transformer's peak. */
export interface PeakMark {
  ts: string;
  ids: string[];
}

const WIDTH = 600;
const HEIGHT = 100;
const RAIN_HEIGHT = 32;
const THIN = "[vector-effect:non-scaling-stroke]";
const TICK_STEPS = [1, 2, 5, 10];
const MAX_TICKS = 4;
const HOUR_MS = 3_600_000;

const hourKey = (ms: number) => Math.floor(ms / HOUR_MS);

function niceTicks(min: number, max: number): number[] {
  const step = TICK_STEPS.find((s) => (max - min) / s < MAX_TICKS) ?? TICK_STEPS[TICK_STEPS.length - 1];
  const first = Math.ceil(min / step) * step;
  return Array.from({ length: Math.floor((max - first) / step) + 1 }, (_, i) => first + i * step);
}

function AxisLabel({ ms }: { ms: number }) {
  const date = new Date(ms);
  return (
    <span>
      <span className="sm:hidden">{date.toLocaleDateString([], { weekday: "short" })}</span>
      <span className="max-sm:hidden">{formatWhen(date)}</span>
    </span>
  );
}

/**
 * Heat index by hour on one °C scale, with marked peaks and, only when it rains, rain in its own panel
 * underneath (its own scale, never a second axis on the same plot). `domain` aligns it with another chart.
 */
export function HeatIndexChart({
  hours,
  marks = [],
  domain,
  markLabel = "Critical peak",
  className,
}: {
  hours: HeatHour[];
  marks?: PeakMark[];
  domain?: [number, number];
  markLabel?: string;
  className?: string;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const times = hours.map((h) => new Date(h.ts).getTime());
  const [start, end] = domain ?? [times[0], times[times.length - 1]];
  const span = Math.max(end - start, 1);
  const values = hours.flatMap((h) => (h.heatC === null ? [] : [h.heatC]));
  const lo = Math.floor(Math.min(...values) - 1);
  const hi = Math.ceil(Math.max(...values) + 1);
  const x = (ms: number) => (WIDTH * (ms - start)) / span;
  const y = (c: number) => HEIGHT * (1 - (c - lo) / Math.max(hi - lo, 1));
  const pct = (v: number, of: number) => `${(100 * v) / of}%`;
  const ticks = niceTicks(lo, hi);
  const rainMax = Math.max(0, ...hours.map((h) => h.rainMm ?? 0));
  const showRain = rainMax > 0;
  // One bar per hour, with a gap between neighbours.
  const barWidth = (0.6 * WIDTH * HOUR_MS) / span;

  // Break the line where an hour has no value.
  const path = hours
    .map((h, i) =>
      h.heatC === null
        ? ""
        : `${i === 0 || hours[i - 1].heatC === null ? "M" : "L"}${x(times[i]).toFixed(1)},${y(h.heatC).toFixed(1)}`,
    )
    .join(" ");

  const marksByHour = new Map<number, string[]>();
  for (const mark of marks) {
    const ms = new Date(mark.ts).getTime();
    if (ms < start || ms > end) continue;
    const key = hourKey(ms);
    marksByHour.set(key, [...(marksByHour.get(key) ?? []), ...mark.ids]);
  }
  const markHours = [...marksByHour.keys()].map((key) => {
    const index = times.findIndex((t) => hourKey(t) === key);
    return { key, ms: key * HOUR_MS, heat: index === -1 ? null : hours[index].heatC };
  });
  const markedCount = [...marksByHour.values()].reduce((sum, ids) => sum + ids.length, 0);

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
    <figure className={cn("m-0 grid gap-2", className)}>
      <figcaption className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted-foreground">
        <span className="inline-flex items-center gap-2">
          <span aria-hidden="true" className="w-5 border-t-2 border-brand" />
          Heat index, °C
        </span>
        {markedCount > 0 && (
          <span className="inline-flex items-center gap-2">
            <span aria-hidden="true" className="size-2.5 rounded-full bg-critical ring-2 ring-card" />
            {markLabel} ({markedCount})
          </span>
        )}
        {showRain && (
          <span className="inline-flex items-center gap-2">
            <span aria-hidden="true" className="h-2.5 w-1.5 rounded-t-sm bg-muted-foreground" />
            Rain, mm
          </span>
        )}
      </figcaption>
      <div
        role="img"
        tabIndex={0}
        aria-label={`Heat index by hour, ${values.length} hours${markedCount > 0 ? `, ${markedCount} ${markLabel.toLowerCase()}s marked` : ""}. Use the arrow keys to read values, or open the table below.`}
        className="relative ml-11 grid touch-pan-y gap-1 rounded-sm"
        onPointerMove={onMove}
        onPointerLeave={() => setHover(null)}
        onKeyDown={onKey}
        onBlur={() => setHover(null)}
      >
        <div className="relative h-24">
          {ticks.map((tick) => (
            <span
              key={tick}
              className="absolute right-[calc(100%+0.5rem)] -translate-y-1/2 text-sm leading-none text-muted-foreground"
              style={{ top: pct(y(tick), HEIGHT) }}
            >
              {tick}°
            </span>
          ))}
          <svg
            aria-hidden="true"
            viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
            preserveAspectRatio="none"
            className="block h-full w-full overflow-visible"
          >
            {ticks.map((tick) => (
              <line key={tick} className={`stroke-border ${THIN}`} x1={0} x2={WIDTH} y1={y(tick)} y2={y(tick)} />
            ))}
            {markHours.map((m) => (
              <line
                key={m.key}
                className={`stroke-critical ${THIN}`}
                x1={x(m.ms)}
                x2={x(m.ms)}
                y1={0}
                y2={HEIGHT}
              />
            ))}
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
          {markHours.map(
            (m) =>
              m.heat !== null && (
                <span
                  key={m.key}
                  aria-hidden="true"
                  className="pointer-events-none absolute size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-critical ring-2 ring-card"
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
              <span>
                <strong>{hovered.heatC === null ? "No value" : `${hovered.heatC.toFixed(1)} °C`}</strong>
                {showRain && ` · ${(hovered.rainMm ?? 0).toFixed(1)} mm rain`}
              </span>
              <span className="text-muted-foreground">{formatWhen(new Date(hovered.ts))}</span>
              {hoveredIds.length > 0 && (
                <span>
                  {markLabel}: {hoveredIds.slice(0, 4).join(", ")}
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
            className="block h-8 w-full border-b"
          >
            {hours.map((h, i) =>
              (h.rainMm ?? 0) > 0 ? (
                <rect
                  key={h.ts}
                  className="fill-muted-foreground"
                  x={x(times[i]) - barWidth / 2}
                  width={barWidth}
                  y={RAIN_HEIGHT * (1 - (h.rainMm ?? 0) / rainMax)}
                  height={(RAIN_HEIGHT * (h.rainMm ?? 0)) / rainMax}
                />
              ) : null,
            )}
          </svg>
        )}
      </div>
      <div className="ml-11 flex justify-between gap-2 text-sm text-muted-foreground">
        <AxisLabel ms={start} />
        <AxisLabel ms={end} />
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
              {showRain && <th className="py-1 text-right font-semibold">Rain</th>}
            </tr>
          </thead>
          <tbody>
            {hours.map((h, i) => (
              <tr key={h.ts} className="border-b">
                <td className="py-1">
                  {formatWhen(new Date(h.ts))}
                  {marksByHour.has(hourKey(times[i])) && `, ${markLabel.toLowerCase()}`}
                </td>
                <td className="py-1 text-right">{h.heatC === null ? "No value" : `${h.heatC.toFixed(1)} °C`}</td>
                {showRain && <td className="py-1 text-right">{(h.rainMm ?? 0).toFixed(1)} mm</td>}
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
