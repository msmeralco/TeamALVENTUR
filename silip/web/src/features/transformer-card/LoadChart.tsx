import { useState, type KeyboardEvent, type PointerEvent } from "react";
import type { Schemas } from "../../shared/api/client";
import { formatPct, formatWhen } from "../../shared/ui";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../shared/ui/components/table";

type Point = Schemas["LoadPoint"];

const WIDTH = 600;
const HEIGHT = 220;
const RATED_FRACTION = 1; // 100% of rating
const HEADROOM = 1.1;
const TICK_STEPS = [0.25, 0.5, 1, 2, 5];
const MAX_TICKS = 6;
const POINTS_PER_HOUR = 4; // 15-minute intervals
const THIN = "[vector-effect:non-scaling-stroke]";
// load_pct = load / (rated_kva x 0.9), from the silip-domain skill.
const RATING_SHARE_OF_NAMEPLATE = 0.9;
const SPARK_WIDTH = 96;
const SPARK_HEIGHT = 24;

/** A tiny, decorative trend line for the collapsed load history row. The chart and table carry the values. */
export function Sparkline({ points }: { points: Point[] }) {
  const yMax = Math.max(RATED_FRACTION, ...points.map((p) => p.load_pct));
  const x = (index: number) => (SPARK_WIDTH * index) / Math.max(points.length - 1, 1);
  const y = (fraction: number) => SPARK_HEIGHT * (1 - fraction / yMax);
  const firstForecast = points.findIndex((p) => p.is_forecast);
  const splitAt = firstForecast === -1 ? points.length : Math.max(firstForecast - 1, 0);
  const path = (from: number, to: number) =>
    points
      .slice(from, to)
      .map((p, i) => `${i === 0 ? "M" : "L"}${x(from + i).toFixed(1)},${y(p.load_pct).toFixed(1)}`)
      .join(" ");
  return (
    <svg aria-hidden="true" viewBox={`0 0 ${SPARK_WIDTH} ${SPARK_HEIGHT}`} className="h-6 w-24 overflow-visible">
      <line
        className={`stroke-muted-foreground [stroke-dasharray:2_3] ${THIN}`}
        x1={0}
        x2={SPARK_WIDTH}
        y1={y(RATED_FRACTION)}
        y2={y(RATED_FRACTION)}
      />
      <path className={`fill-none stroke-foreground stroke-[1.5] ${THIN}`} d={path(0, splitAt + 1)} />
      {firstForecast !== -1 && (
        <path
          className={`fill-none stroke-foreground stroke-[1.5] [stroke-dasharray:4_3] ${THIN}`}
          d={path(splitAt, points.length)}
        />
      )}
    </svg>
  );
}

/** Day and time on wide screens; the day alone on phones, so it does not collide with "Now". */
function AxisLabel({ ts }: { ts: string }) {
  return (
    <span>
      <span className="sm:hidden">{new Date(ts).toLocaleDateString([], { weekday: "short" })}</span>
      <span className="max-sm:hidden">{formatWhen(new Date(ts))}</span>
    </span>
  );
}

/**
 * Load as % of rating: last 48 h solid, next 24 h forecast dashed, with a 100% line.
 * `nowLabel` names the line where the forecast starts; a fixed example says "Snapshot", since it is not now.
 */
export function LoadChart({
  points,
  ratedKva,
  nowLabel = "Now",
}: {
  points: Point[];
  ratedKva: number;
  nowLabel?: string;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const yMax = Math.max(RATED_FRACTION * 1.2, ...points.map((p) => p.load_pct * HEADROOM));
  const x = (index: number) => (WIDTH * index) / Math.max(points.length - 1, 1);
  const y = (fraction: number) => HEIGHT * (1 - fraction / yMax);
  const xPct = (index: number) => `${(100 * x(index)) / WIDTH}%`;
  const yPct = (fraction: number) => `${(100 * y(fraction)) / HEIGHT}%`;
  const nowIndex = points.findIndex((p) => p.is_forecast);
  // The forecast line starts at the last measured point so the two lines join.
  const splitAt = nowIndex === -1 ? points.length : Math.max(nowIndex - 1, 0);
  const path = (from: number, to: number) =>
    points
      .slice(from, to)
      .map((p, i) => `${i === 0 ? "M" : "L"}${x(from + i).toFixed(1)},${y(p.load_pct).toFixed(1)}`)
      .join(" ");
  const tickStep = TICK_STEPS.find((step) => yMax / step < MAX_TICKS) ?? TICK_STEPS[TICK_STEPS.length - 1];
  const ticks = Array.from({ length: Math.floor(yMax / tickStep) + 1 }, (_, i) => i * tickStep);

  const onMove = (event: PointerEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect();
    const fraction = (event.clientX - box.left) / box.width;
    setHover(Math.min(points.length - 1, Math.max(0, Math.round(fraction * (points.length - 1)))));
  };
  const hovered = hover === null ? undefined : points[hover];

  // Arrow keys step one hour, Home and End jump to the ends. Same readout as the pointer.
  const onKey = (event: KeyboardEvent<SVGSVGElement>) => {
    const last = points.length - 1;
    const from = hover ?? (nowIndex > 0 ? nowIndex : last);
    const moves: Record<string, number> = {
      ArrowLeft: from - POINTS_PER_HOUR,
      ArrowRight: from + POINTS_PER_HOUR,
      Home: 0,
      End: last,
    };
    const target = moves[event.key];
    if (target === undefined) return;
    event.preventDefault();
    setHover(Math.min(last, Math.max(0, target)));
  };
  const ratingKva = ratedKva * RATING_SHARE_OF_NAMEPLATE;

  return (
    <figure className="m-0 grid gap-2">
      <figcaption className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted-foreground">
        <span className="inline-flex items-center gap-2">
          <span aria-hidden="true" className="w-5 border-t-2 border-foreground" />
          Measured, last 48 h
        </span>
        <span className="inline-flex items-center gap-2">
          <span aria-hidden="true" className="w-5 border-t-2 border-dashed border-foreground" />
          Forecast, next 24 h
        </span>
        <span className="inline-flex items-center gap-2">
          <span aria-hidden="true" className="w-5 border-t-2 border-dotted border-muted-foreground" />
          100% = 90% of the {ratedKva} kVA nameplate ({Number(ratingKva.toFixed(2))} kVA)
        </span>
      </figcaption>
      <div className="relative ml-11 h-56">
        {ticks.map((tick) => (
          <span
            key={tick}
            className="absolute right-[calc(100%+0.5rem)] -translate-y-1/2 text-sm leading-none text-muted-foreground"
            style={{ top: yPct(tick) }}
          >
            {formatPct(tick)}
          </span>
        ))}
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          preserveAspectRatio="none"
          role="img"
          tabIndex={0}
          aria-label={`Load as percent of rating over ${Math.round(points.length / POINTS_PER_HOUR)} hours. Use the arrow keys to read values, or open the table below.`}
          className="block h-full w-full touch-pan-y overflow-visible rounded-sm"
          onPointerMove={onMove}
          onPointerLeave={() => setHover(null)}
          onKeyDown={onKey}
          onBlur={() => setHover(null)}
        >
          {ticks.map((tick) => (
            <line key={tick} className={`stroke-border ${THIN}`} x1={0} x2={WIDTH} y1={y(tick)} y2={y(tick)} />
          ))}
          <line
            className={`stroke-muted-foreground [stroke-dasharray:2_4] ${THIN}`}
            x1={0}
            x2={WIDTH}
            y1={y(RATED_FRACTION)}
            y2={y(RATED_FRACTION)}
          />
          {nowIndex > 0 && (
            <line className={`stroke-muted-foreground ${THIN}`} x1={x(nowIndex)} x2={x(nowIndex)} y1={0} y2={HEIGHT} />
          )}
          <path className={`fill-none stroke-foreground stroke-2 ${THIN}`} d={path(0, splitAt + 1)} />
          {nowIndex !== -1 && (
            <path
              className={`fill-none stroke-foreground stroke-2 [stroke-dasharray:6_4] ${THIN}`}
              d={path(splitAt, points.length)}
            />
          )}
          {hover !== null && (
            <line className={`stroke-muted-foreground ${THIN}`} x1={x(hover)} x2={x(hover)} y1={0} y2={HEIGHT} />
          )}
        </svg>
        {hovered !== undefined && hover !== null && (
          <>
            <span
              className="pointer-events-none absolute size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-foreground ring-2 ring-card"
              style={{ left: xPct(hover), top: yPct(hovered.load_pct) }}
            />
            <div
              aria-live="polite"
              className={
                "pointer-events-none absolute top-0 grid rounded-lg border bg-popover px-3 py-2 text-sm whitespace-nowrap shadow-lg " +
                (hover > points.length / 2 ? "-translate-x-[calc(100%+0.5rem)]" : "translate-x-2")
              }
              style={{ left: xPct(hover) }}
            >
              <span>
                <strong>{formatPct(hovered.load_pct)}</strong> · {hovered.kw.toFixed(1)} kW
              </span>
              <span className="text-muted-foreground">
                {formatWhen(new Date(hovered.ts))}
                {hovered.is_forecast ? ", forecast" : ""}
              </span>
            </div>
          </>
        )}
      </div>
      <div className="relative ml-11 flex justify-between gap-2 text-sm text-muted-foreground">
        <AxisLabel ts={points[0].ts} />
        {nowIndex > 0 && (
          <span className="absolute -translate-x-1/2" style={{ left: xPct(nowIndex) }}>
            {nowLabel}
          </span>
        )}
        <AxisLabel ts={points[points.length - 1].ts} />
      </div>
      <details className="mt-2">
        <summary className="flex min-h-11 cursor-pointer items-center text-sm text-muted-foreground sm:min-h-0">
          Show hourly values as a table
        </summary>
        <Table className="mt-2">
          <TableHeader>
            <TableRow>
              <TableHead>Time</TableHead>
              <TableHead className="text-right">Load</TableHead>
              <TableHead className="text-right">kW</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {points
              .filter((_, i) => i % POINTS_PER_HOUR === 0)
              .map((p) => (
                <TableRow key={p.ts}>
                  <TableCell>
                    {formatWhen(new Date(p.ts))}
                    {p.is_forecast ? " (forecast)" : ""}
                  </TableCell>
                  <TableCell className="text-right">{formatPct(p.load_pct)}</TableCell>
                  <TableCell className="text-right">{p.kw.toFixed(1)}</TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </details>
    </figure>
  );
}
