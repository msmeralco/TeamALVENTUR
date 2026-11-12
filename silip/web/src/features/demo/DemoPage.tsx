import { useQuery } from "@tanstack/react-query";
import { QRCodeSVG } from "qrcode.react";
import { api, unwrap, type Schemas } from "../../shared/api/client";
import { PageHead, TierBadge, cn, formatPct } from "../../shared/ui";
import { Card } from "../../shared/ui/components/card";
import { useDocumentTitle } from "../../shared/ui/feedback";

type Snapshot = Schemas["BenchSnapshot"];
type TransformerState = Schemas["BenchTransformerState"];

// The rig sends a reading every 2 s; polling at the same pace keeps the page within one sample.
const POLL_MS = 2_000;
const QR_SIZE_PX = 132;
const BAR_CAP = 1.5; // the load bar fills at 150% of rating, so Critical still shows headroom past 100%

const short = (transformerId: string) => transformerId.replace(/^BENCH-/, "");
const watts = (w: number | null | undefined) => (w == null ? "–" : `${w.toFixed(2)} W`);
const volts = (v: number | null | undefined) => (v == null ? "–" : `${v.toFixed(2)} V`);

// Past this, a rounded "100%" would overstate what a statistical test can say.
const CONFIDENCE_CEILING = 0.99;
const confidenceText = (c: number) => (c >= CONFIDENCE_CEILING ? "over 99%" : formatPct(c));

const BAR_CLASS = { OK: "bg-ok", Watch: "bg-watch", Critical: "bg-critical" } as const;

function ModeLabel({ snapshot }: { snapshot: Snapshot }) {
  if (snapshot.mode === null) return <span className="text-sm text-muted-foreground">Waiting for readings</span>;
  return (
    <span className="justify-self-start rounded-full bg-secondary px-2.5 py-0.5 text-sm font-semibold text-muted-foreground">
      {snapshot.mode === "live" ? "Live rig" : "Replay (simulated)"}
    </span>
  );
}

function TransformerCard({ t }: { t: TransformerState }) {
  return (
    <Card className="gap-4 px-5 py-5 shadow-none">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-xl">Transformer {short(t.transformer_id)}</h2>
        {t.powered ? (
          <TierBadge tier={t.tier} />
        ) : (
          <span className="rounded-full bg-secondary px-2.5 py-0.5 text-sm font-semibold">No power</span>
        )}
      </div>
      <div>
        <p className="font-display text-3xl font-bold tabular-nums">
          {watts(t.total_w)} <span className="text-xl text-muted-foreground">of {t.rated_w} W</span>
        </p>
        <div className="mt-2 h-3 overflow-hidden rounded-full bg-muted" aria-hidden="true">
          <div
            className={cn("h-full rounded-full transition-[width] duration-500", BAR_CLASS[t.tier])}
            style={{ width: `${Math.min(t.load_pct / BAR_CAP, 1) * 100}%` }}
          />
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          {formatPct(t.load_pct)} of rating · built from {t.homes_reporting} of {t.homes_on_record} {t.homes_on_record === 1 ? "home" : "homes"} by SIN
        </p>
      </div>
      <ul className="grid gap-1 text-sm">
        {t.reasons.map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>
      <table className="w-full text-sm tabular-nums">
        <thead className="text-left text-muted-foreground">
          <tr>
            <th className="py-1 font-normal">Home</th>
            <th className="py-1 text-right font-normal">Power</th>
            <th className="py-1 text-right font-normal">Voltage</th>
          </tr>
        </thead>
        <tbody>
          {t.homes.map((home) => (
            <tr key={home.label} className="border-t">
              <td className="py-1.5">{home.label}</td>
              <td className="py-1.5 text-right">{home.powered ? watts(home.watts) : "No power"}</td>
              <td className="py-1.5 text-right">{home.powered ? volts(home.volts) : "–"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

function Fingerprints({ snapshot }: { snapshot: Snapshot }) {
  const flags = snapshot.fingerprints.filter((f) => f.mismatch);
  if (flags.length === 0) return null;
  return (
    <Card role="status" className="gap-1 px-5 py-4 shadow-none">
      {flags.map((f) => (
        <div key={f.home}>
          <p className="font-semibold">
            {f.home}: records say {short(f.record_transformer)}, voltage says {short(f.voltage_transformer ?? "")}{" "}
            (confidence {confidenceText(f.confidence)})
          </p>
          <p className="text-sm text-muted-foreground">
            Its voltage dips when {short(f.voltage_transformer ?? "")} is loaded, not {short(f.record_transformer)}.
          </p>
        </div>
      ))}
    </Card>
  );
}

/** Public live demo: the bench rig's mock homes summed by SIN into two transformers. */
export function DemoPage() {
  useDocumentTitle("Live demo");
  const query = useQuery({
    queryKey: ["bench"],
    queryFn: async () => unwrap(await api.GET("/api/v1/bench")),
    refetchInterval: POLL_MS,
    refetchIntervalInBackground: true,
  });
  const snapshot = query.data;
  return (
    <section className="grid gap-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <PageHead
          className="mb-0 max-w-xl"
          title="Mini barangay, live"
          lede="Each home has a clamp. SILIP sums the homes by SIN into their transformer and checks it against its rating."
        >
          {snapshot && <ModeLabel snapshot={snapshot} />}
        </PageHead>
        <figure className="m-0 grid justify-items-center gap-1 max-sm:hidden">
          <div className="rounded-lg bg-[var(--qr-background)] p-2 text-[var(--qr-foreground)]">
            <QRCodeSVG value={window.location.href} size={QR_SIZE_PX} fgColor="currentColor" bgColor="transparent" />
          </div>
          <figcaption className="text-sm text-muted-foreground">Scan to follow on your phone</figcaption>
        </figure>
      </div>

      {query.isError && !snapshot && (
        <Card role="alert" className="px-5 py-4 shadow-none">
          Could not reach the rig's data. Retrying every {POLL_MS / 1000} s.
        </Card>
      )}
      {!snapshot && !query.isError && <div className="h-96 animate-pulse rounded-xl bg-muted" aria-busy="true" />}
      {snapshot && (
        <>
          <Fingerprints snapshot={snapshot} />
          {snapshot.mode === null && (
            <Card className="px-5 py-4 shadow-none">Waiting for the rig. Power it on, or start the simulator.</Card>
          )}
          <div className="grid items-start gap-5 md:grid-cols-2">
            {snapshot.transformers.map((t) => (
              <TransformerCard key={t.transformer_id} t={t} />
            ))}
          </div>
        </>
      )}
    </section>
  );
}
