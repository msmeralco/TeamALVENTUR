import { useEffect, type ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { OutageCheck } from "../features/outages/OutagesPage";
import { LoadChart } from "../features/transformer-card/LoadChart";
import { useAuth } from "../shared/auth";
import { SimulatedLabel, TierBadge, formatPct } from "../shared/ui";
import { Button } from "../shared/ui/components/button";
import { Card } from "../shared/ui/components/card";
import { useDocumentTitle } from "../shared/ui/feedback";
import { EXAMPLE_TRANSFORMER } from "./engineerExample";

const SECTION = "grid scroll-mt-24 gap-6";

/** Each step: a short label drawn in the diagram, and one sentence (split into lines for the phone diagram). */
const STEPS = [
  { label: "Household clamp", lines: ["A clamp on an opted-in home's wiring", "reads its power use, after the meter."] },
  { label: "Summed per transformer", lines: ["Readings are added up per transformer,", "matched by a hashed Service ID."] },
  { label: "Load and risk", lines: ["SILIP estimates the load and", "forecasts the next 24 hours."] },
  { label: "Map and outages", lines: ["Engineers see a risk map.", "Residents see open outages."] },
];

const NODE_R = 20;
const GAP = 8;

/** Wide screens: four nodes in a row, labels under them. Columns line up with the sentences below. */
function DiagramRow() {
  const step = 240;
  const cx = (i: number) => step / 2 + i * step;
  return (
    <svg aria-hidden="true" viewBox="0 0 960 96" className="block h-auto w-full max-sm:hidden">
      {STEPS.slice(1).map((_, i) => (
        <line
          key={i}
          x1={cx(i) + NODE_R + GAP}
          x2={cx(i + 1) - NODE_R - GAP}
          y1={28}
          y2={28}
          stroke="var(--brand)"
          strokeWidth={2}
          markerEnd="url(#how-arrow-row)"
        />
      ))}
      <defs>
        <marker id="how-arrow-row" viewBox="0 0 10 10" refX={9} refY={5} markerWidth={8} markerHeight={8} orient="auto">
          <path d="M1 1 9 5 1 9" fill="none" stroke="var(--brand)" strokeWidth={1.5} />
        </marker>
      </defs>
      {STEPS.map((s, i) => (
        <g key={s.label}>
          <circle cx={cx(i)} cy={28} r={NODE_R} fill="var(--card)" stroke="var(--brand)" strokeWidth={2} />
          <text
            x={cx(i)}
            y={34}
            textAnchor="middle"
            fill="var(--foreground)"
            fontSize={16}
            fontWeight={700}
            fontFamily="var(--font-display)"
          >
            {i + 1}
          </text>
          <text x={cx(i)} y={84} textAnchor="middle" fill="var(--foreground)" fontSize={15} fontWeight={600}>
            {s.label}
          </text>
        </g>
      ))}
    </svg>
  );
}

/** Phones: the same four nodes in a column, with each sentence beside its node. */
function DiagramColumn() {
  const step = 104;
  const cy = (i: number) => 24 + i * step;
  return (
    <svg aria-hidden="true" viewBox={`0 0 340 ${cy(STEPS.length - 1) + 48}`} className="block h-auto w-full sm:hidden">
      <defs>
        <marker id="how-arrow-col" viewBox="0 0 10 10" refX={9} refY={5} markerWidth={8} markerHeight={8} orient="auto">
          <path d="M1 1 9 5 1 9" fill="none" stroke="var(--brand)" strokeWidth={1.5} />
        </marker>
      </defs>
      {STEPS.slice(1).map((_, i) => (
        <line
          key={i}
          x1={24}
          x2={24}
          y1={cy(i) + NODE_R + GAP}
          y2={cy(i + 1) - NODE_R - GAP}
          stroke="var(--brand)"
          strokeWidth={2}
          markerEnd="url(#how-arrow-col)"
        />
      ))}
      {STEPS.map((s, i) => (
        <g key={s.label}>
          <circle cx={24} cy={cy(i)} r={NODE_R} fill="var(--card)" stroke="var(--brand)" strokeWidth={2} />
          <text
            x={24}
            y={cy(i) + 6}
            textAnchor="middle"
            fill="var(--foreground)"
            fontSize={16}
            fontWeight={700}
            fontFamily="var(--font-display)"
          >
            {i + 1}
          </text>
          <text x={60} y={cy(i) - 2} fill="var(--foreground)" fontSize={15} fontWeight={600}>
            {s.label}
          </text>
          {s.lines.map((line, j) => (
            <text key={line} x={60} y={cy(i) + 20 + j * 19} fill="var(--muted-foreground)" fontSize={14}>
              {line}
            </text>
          ))}
        </g>
      ))}
    </svg>
  );
}

function HowItWorks() {
  return (
    <section id="how-it-works" aria-labelledby="how-it-works-title" className={SECTION}>
      <h2 id="how-it-works-title" className="text-xl">
        How it works
      </h2>
      <div className="grid gap-3">
        <DiagramRow />
        <DiagramColumn />
        <ol className="grid grid-cols-4 gap-6 text-center text-sm text-muted-foreground max-sm:sr-only">
          {STEPS.map((s) => (
            <li key={s.label} className="text-balance">
              <span className="sr-only">{s.label}: </span>
              {s.lines.join(" ")}
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="font-semibold tabular-nums">{children}</dd>
    </div>
  );
}

/**
 * A fixed example, not live data: the transformer endpoints need an engineer sign-in.
 * It is built from the same parts as the real transformer card and labeled as simulated.
 */
function EngineerPreview() {
  const t = EXAMPLE_TRANSFORMER;
  return (
    <section id="engineers" aria-labelledby="engineers-title" className={SECTION}>
      <div className="grid gap-2">
        <h2 id="engineers-title" className="text-xl">
          What engineers see
        </h2>
        <p className="max-w-2xl text-muted-foreground">
          Every transformer gets a card like this one. The reasons come first, then the load curve and a 24-hour
          forecast.
        </p>
      </div>
      <Card className="gap-5 px-4 shadow-none sm:px-6">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="mr-2 text-xl">{t.transformer_id}</h3>
          <TierBadge tier={t.risk.tier} />
          <SimulatedLabel show />
          <span className="text-sm text-muted-foreground">Example</span>
        </div>
        <ul className="grid list-disc gap-1 pl-5 marker:text-muted-foreground">
          {t.risk.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
        <dl className="grid grid-cols-[repeat(auto-fit,minmax(8rem,1fr))] gap-4 border-t pt-4">
          <Fact label="Confidence">{formatPct(t.risk.confidence)}</Fact>
          <Fact label="Coverage">{formatPct(t.risk.coverage_pct)} of homes</Fact>
          <Fact label="Rating">
            {t.rated_kva} kVA, {t.homes} homes
          </Fact>
        </dl>
        <LoadChart points={[...t.load]} ratedKva={t.rated_kva} nowLabel="Snapshot" />
      </Card>
    </section>
  );
}

const PRIVACY = [
  "Households opt in. No clamp goes in without the owner's consent.",
  "Service IDs are stored only as salted hashes, never as plain numbers.",
  "A household sees only its own usage.",
  "SILIP never touches Meralco's meter, seal, service drop or transformer.",
];

function Privacy() {
  return (
    <section id="privacy" aria-labelledby="privacy-title" className={SECTION}>
      <h2 id="privacy-title" className="text-xl">
        Privacy, in plain words
      </h2>
      <ul className="grid max-w-2xl list-disc gap-2 pl-5 marker:text-brand">
        {PRIVACY.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
    </section>
  );
}

const DOORS = [
  {
    title: "For engineers",
    text: "See which transformers may overload in the next 24 hours, with coverage and confidence.",
    to: "/engineer",
    open: "Open risk map",
  },
  {
    title: "For households",
    text: "See your home's own usage for the last 7 days. Only you can see it.",
    to: "/me/usage",
    open: "Open my usage",
  },
];

function Doors() {
  const { user, signIn } = useAuth();
  return (
    <section id="sign-in" aria-labelledby="sign-in-title" className={SECTION}>
      <h2 id="sign-in-title" className="text-xl">
        Sign in for more
      </h2>
      <div className="divide-y border-y">
        {DOORS.map((door) => (
          <div
            key={door.title}
            className="grid items-center gap-x-6 gap-y-2 py-5 sm:grid-cols-[12rem_1fr_auto]"
          >
            <h3 className="text-base font-semibold">{door.title}</h3>
            <p className="text-muted-foreground">{door.text}</p>
            {user === null ? (
              <Button
                variant="outline"
                className="min-h-11 w-fit rounded-full"
                onClick={() => void signIn(door.to)}
              >
                Sign in
                <span className="sr-only"> {door.title.toLowerCase()}</span>
              </Button>
            ) : (
              <Button asChild variant="outline" className="min-h-11 w-fit rounded-full">
                <Link to={door.to}>{door.open}</Link>
              </Button>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

/** React Router does not scroll to "#how-it-works" by itself; do it whenever the hash changes. */
function useScrollToHash() {
  const { hash, key } = useLocation();
  useEffect(() => {
    if (hash === "") return;
    document.getElementById(decodeURIComponent(hash.slice(1)))?.scrollIntoView?.({ block: "start" });
  }, [hash, key]);
}

/** Public landing page: the outage check first, then what SILIP is, what engineers see, privacy and sign-in. */
export function LandingPage() {
  useDocumentTitle();
  useScrollToHash();
  return (
    <div className="grid gap-16 sm:gap-24">
      <section aria-labelledby="hero-title" className="grid items-start gap-10 lg:grid-cols-2 lg:gap-16">
        <div className="grid justify-items-start gap-4">
          <span className="grid place-items-center rounded-2xl bg-logo-tile p-1">
            <img src="/brand/silip-mark-512.png" alt="" width={80} height={80} className="size-20" />
          </span>
          <h1 id="hero-title" className="text-3xl tracking-tight text-balance">
            SILIP estimates the load on each neighborhood transformer.
          </h1>
          <p className="max-w-xl text-muted-foreground">
            It adds up opt-in readings from homes. Grid engineers see which transformers may overload. Residents can
            check for outages right here.
          </p>
        </div>
        <div className="grid gap-4">
          <h2 className="text-xl">Is the power out near you?</h2>
          <OutageCheck />
        </div>
      </section>
      <HowItWorks />
      <EngineerPreview />
      <Privacy />
      <Doors />
    </div>
  );
}
