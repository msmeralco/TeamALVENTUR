import { Check, ClipboardCopy } from "lucide-react";
import { useEffect, useState } from "react";
import type { Schemas } from "../../shared/api/client";
import type { Action } from "../../shared/risk";
import { formatPct, formatWhen } from "../../shared/ui";
import { Badge } from "../../shared/ui/components/badge";
import { Button } from "../../shared/ui/components/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../shared/ui/components/card";

type TransformerCard = Schemas["TransformerCard"];
type Driver = Schemas["silip__shared__scores__domain__Driver"];

const COPIED_MS = 2000;

/** What each action asks of the engineer, in one plain sentence. */
const ACTION_TEXT: Record<Action, string> = {
  "Inspect before peak": "Send a crew to check this transformer before the forecast peak.",
  "Add clamps": "Too few homes report to trust this estimate. More clamps would raise confidence.",
  "Fix clamps": "Installed clamps are offline and lowering confidence. Bring them back online.",
  "Plan upgrade": "Load keeps running near or over rating. Consider a capacity upgrade in planning.",
  Monitor: "No action needed now. Keep watching the forecast.",
};

/** A plain-text summary to paste into a work order system. Nothing is sent anywhere. */
export function workOrderText(card: TransformerCard): string {
  const peak = card.peak_ts == null ? "in the next 24 h" : `at ${formatWhen(new Date(card.peak_ts))}`;
  return [
    `${card.transformer_id} (${card.rated_kva} kVA): ${card.action ?? "No action"}`,
    `Tier ${card.risk.tier}. Peak ${formatPct(card.risk.peak_load_pct)} of rating ${peak}.`,
    ...card.risk.reasons.map((r) => `- ${r}`),
    `Coverage ${formatPct(card.risk.coverage_pct)} of homes, confidence ${formatPct(card.risk.confidence)}.`,
    `Location ${card.lat.toFixed(5)}, ${card.lon.toFixed(5)}.`,
    ...(card.is_simulated ? ["Simulated data."] : []),
  ].join("\n");
}

function scrollToId(id: string) {
  const target = document.getElementById(id);
  target?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  target?.focus({ preventScroll: true });
}

/** The one primary button: copy a work-order summary for an inspection, else jump to the facts that matter. */
function PrimaryAction({ card }: { card: TransformerCard }) {
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(false), COPIED_MS);
    return () => window.clearTimeout(timer);
  }, [copied]);
  const button = "min-h-11 self-start rounded-full sm:min-h-9";
  if (card.action === "Inspect before peak") {
    const copy = async () => {
      try {
        await navigator.clipboard.writeText(workOrderText(card));
        setCopied(true);
      } catch {
        // Clipboard blocked (http, permissions): every fact is still on this page.
      }
    };
    return (
      <Button className={button} onClick={() => void copy()}>
        {copied ? <Check aria-hidden="true" /> : <ClipboardCopy aria-hidden="true" />}
        <span aria-live="polite">{copied ? "Copied" : "Copy work order summary"}</span>
      </Button>
    );
  }
  const clampAction = card.action === "Add clamps" || card.action === "Fix clamps";
  return (
    <Button className={button} onClick={() => scrollToId(clampAction ? "clamp-health" : "load")}>
      {clampAction ? "See clamp health" : "See load forecast"}
    </Button>
  );
}

export function ActionBlock({ card }: { card: TransformerCard }) {
  return (
    <Card className="gap-3 px-6 py-5 shadow-none">
      <h2 className="text-xl">{card.action === null || card.action === undefined ? "No action scored" : card.action}</h2>
      <p>
        {card.action == null
          ? "This transformer was scored before actions existed. The next scoring run adds one."
          : ACTION_TEXT[card.action]}
      </p>
      {card.action === "Inspect before peak" && (
        <p className="text-sm text-muted-foreground">Copies a text summary to paste into your work order system.</p>
      )}
      <PrimaryAction card={card} />
      {card.open_outage && <p className="text-sm">An outage is open here, so Inspect before peak is not offered.</p>}
      {card.risk.tier !== "OK" && (
        <p className="text-sm text-muted-foreground">No per-phase data, so rebalancing can't be assessed.</p>
      )}
    </Card>
  );
}

/**
 * Why it is flagged: the drivers as sentences, plus small bars when the model gave per-feature
 * contributions. The rules scorer gives none, so then the sentences stand alone.
 */
export function Drivers({ card }: { card: TransformerCard }) {
  const drivers: Driver[] =
    (card.drivers ?? []).length > 0
      ? (card.drivers ?? [])
      : card.risk.reasons.map((label) => ({ feature: label, label, source: "" }));
  const scale = Math.max(0, ...drivers.map((d) => Math.abs(d.contribution ?? 0)));
  const withBars = scale > 0;
  return (
    <Card className="shadow-none">
      <CardHeader>
        <CardTitle className="font-display text-xl">
          <h2>Why {card.risk.tier}</h2>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {drivers.length === 0 ? (
          <p className="text-sm text-muted-foreground">No reasons given.</p>
        ) : (
          <ol className="grid gap-3">
            {drivers.map((d) => {
              const c = d.contribution ?? null;
              return (
                <li key={d.feature} className="grid gap-1">
                  <p>
                    {d.label}
                    {d.source !== "" && <span className="text-sm text-muted-foreground"> Source: {d.source}.</span>}
                  </p>
                  {withBars && c !== null && (
                    <div className="flex items-center gap-3 text-sm text-muted-foreground">
                      <span aria-hidden="true" className="h-2 w-40 max-w-[50%] rounded-full bg-muted">
                        <span
                          className={`block h-full rounded-full ${c >= 0 ? "bg-foreground" : "bg-muted-foreground"}`}
                          style={{ width: `${(100 * Math.abs(c)) / scale}%` }}
                        />
                      </span>
                      <span>
                        {c >= 0 ? "Raises risk" : "Lowers risk"} ({c >= 0 ? "+" : "−"}
                        {Math.abs(c).toFixed(2)})
                      </span>
                    </div>
                  )}
                </li>
              );
            })}
          </ol>
        )}
        {withBars && (
          <p className="mt-3 text-sm text-muted-foreground">Bars: how much each reason moved the model score.</p>
        )}
      </CardContent>
    </Card>
  );
}

const signed = (kw: number) => `${kw >= 0 ? "+" : "−"}${Math.abs(kw).toFixed(1)} kW`;

export function EvBlock({ card }: { card: TransformerCard }) {
  const { ev } = card;
  const km = ev.radius_m / 1000;
  const scenario = ev.adoption_scenario;
  return (
    <Card id="ev" className="gap-3 px-6 py-5 shadow-none">
      <h2 className="text-xl">EV charging nearby</h2>
      <p>
        {ev.stations_within === 0
          ? `No public chargers within ${km} km.`
          : `${ev.stations_within} public ${ev.stations_within === 1 ? "charger" : "chargers"} within ${km} km.`}
        {ev.nearest_station_m !== null && ` Nearest is ${Math.round(ev.nearest_station_m)} m away.`}
        <span className="text-sm text-muted-foreground"> Source: DOE.</span>
      </p>
      {ev.stations.length > 0 && (
        <ul className="grid gap-1 text-sm text-muted-foreground">
          {ev.stations.slice(0, 3).map((s) => (
            <li key={s.station_id}>
              {s.name}
              {s.city !== null && `, ${s.city}`}
            </li>
          ))}
        </ul>
      )}
      <p className="text-sm">
        {card.ev_evening_step_kw == null
          ? "Not enough history to measure the evening load step."
          : `Evening load step ${signed(card.ev_evening_step_kw)}: last 7 days against days 8 to 28. Measured.`}
      </p>
      <div className="grid gap-1 border-t pt-3">
        {scenario === null ? (
          <p className="text-sm text-muted-foreground">Adoption stats not loaded.</p>
        ) : (
          <>
            <Badge variant="secondary" className="px-2.5 font-semibold text-muted-foreground">
              {scenario.label}
            </Badge>
            <p className="text-sm">
              {scenario.geography}, {scenario.metric.replaceAll("_", " ").replace(/ev/, "EV")} (
              {scenario.vehicle_class.toUpperCase()}), {scenario.period}: {scenario.value.toLocaleString()}{" "}
              {scenario.unit}.
              {scenario.source_url !== null && (
                <>
                  {" "}
                  <a href={scenario.source_url} target="_blank" rel="noreferrer" className="text-muted-foreground">
                    Source<span className="sr-only"> (opens in a new tab)</span>
                  </a>
                </>
              )}
            </p>
          </>
        )}
      </div>
    </Card>
  );
}

export function ClampBlock({ card }: { card: TransformerCard }) {
  const health = card.clamp_health ?? null;
  const toTarget = card.clamps_to_target ?? null;
  return (
    <Card id="clamp-health" tabIndex={-1} className="gap-3 px-6 py-5 shadow-none outline-none">
      <h2 className="text-xl">Clamp health</h2>
      {toTarget !== null && (
        <p className="font-semibold">
          {toTarget === 0
            ? "Coverage is at target."
            : `${toTarget} more ${toTarget === 1 ? "clamp" : "clamps"} for target.`}
        </p>
      )}
      {health === null ? (
        <p className="text-sm text-muted-foreground">No clamps installed.</p>
      ) : (
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm tabular-nums">
          <dt className="text-muted-foreground">Clamps online</dt>
          <dd>
            {health.clamps_online} of {health.clamps_installed} installed
          </dd>
          <dt className="text-muted-foreground">Homes reporting</dt>
          <dd>
            {health.homes_reporting} of {health.homes} ({formatPct(health.reporting_pct)})
          </dd>
        </dl>
      )}
    </Card>
  );
}
