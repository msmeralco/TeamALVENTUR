import { useEffect, type ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { OutageCheck } from "../features/outages/OutagesPage";
import { LoadChart } from "../features/transformer-card/LoadChart";
import { useAuth, type Group } from "../shared/auth";
import { SimulatedLabel, TierBadge, formatPct } from "../shared/ui";
import { Button } from "../shared/ui/components/button";
import { Card } from "../shared/ui/components/card";
import { useDocumentTitle } from "../shared/ui/feedback";
import { EXAMPLE_TRANSFORMER } from "./engineerExample";

const SECTION = "grid scroll-mt-24 gap-6";

/** Each step: a short title and one sentence. */
const STEPS = [
  { label: "Household clamp", text: "A clamp on an opted-in home's wiring reads its power use, after the meter." },
  { label: "Summed per transformer", text: "Readings are added up per transformer, matched by a hashed Service ID." },
  { label: "Load and risk", text: "SILIP estimates the load and forecasts the next 24 hours." },
  { label: "Map and outages", text: "Engineers see a risk map. Residents see open outages." },
];

/**
 * The arrow from one step's circle to the next. Below lg the steps stack, so it runs down from the circle;
 * from lg they sit in a row of equal columns with a 24px gap, so it runs right to the next column's circle.
 */
function Connector() {
  return (
    <span
      aria-hidden="true"
      className="absolute top-12 -bottom-4 left-5 flex -translate-x-1/2 flex-col items-center text-brand lg:top-5 lg:right-[calc(-50%+0.25rem)] lg:bottom-auto lg:left-[calc(50%+1.75rem)] lg:translate-x-0 lg:-translate-y-1/2 lg:flex-row"
    >
      <span className="w-0.5 flex-1 bg-current lg:h-0.5 lg:w-auto" />
      <svg viewBox="0 0 10 10" className="-mt-2 size-2.5 rotate-90 lg:mt-0 lg:-ml-2 lg:rotate-0">
        <path d="M1 1 9 5 1 9" fill="none" stroke="currentColor" strokeWidth={1.5} />
      </svg>
    </span>
  );
}

function HowItWorks() {
  return (
    <section id="how-it-works" aria-labelledby="how-it-works-title" className={SECTION}>
      <h2 id="how-it-works-title" className="text-xl">
        How it works
      </h2>
      <ol className="grid gap-6 lg:grid-cols-4">
        {STEPS.map((s, i) => (
          <li
            key={s.label}
            className="relative grid grid-cols-[2.5rem_1fr] items-start gap-x-4 lg:grid-cols-1 lg:justify-items-center lg:gap-y-3 lg:text-center"
          >
            <span
              aria-hidden="true"
              className="grid size-10 place-items-center rounded-full border-2 border-brand bg-card font-display font-bold"
            >
              {i + 1}
            </span>
            <div className="grid gap-1">
              <h3 className="text-base font-semibold">{s.label}</h3>
              <p className="text-sm text-balance text-muted-foreground">{s.text}</p>
            </div>
            {i < STEPS.length - 1 && <Connector />}
          </li>
        ))}
      </ol>
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

const DOORS: { title: string; text: string; to: string; open: string; group: Group }[] = [
  {
    title: "For engineers",
    text: "See which transformers may overload in the next 24 hours, with coverage and confidence.",
    to: "/engineer",
    open: "Open risk map",
    group: "engineers",
  },
  {
    title: "For households",
    text: "See your home's own usage for the last 7 days. Only you can see it.",
    to: "/me/usage",
    open: "Open my usage",
    group: "households",
  },
];

/** Signed out: both doors, each with Sign in. Signed in: only the doors to the viewer's own views. */
function Doors() {
  const { user, signIn, hasGroup } = useAuth();
  const doors = user === null ? DOORS : DOORS.filter((door) => hasGroup(door.group));
  if (doors.length === 0) return null;
  return (
    <section id="sign-in" aria-labelledby="sign-in-title" className={SECTION}>
      <h2 id="sign-in-title" className="text-xl">
        {user === null ? "Sign in for more" : "Your views"}
      </h2>
      <div className="divide-y border-y">
        {doors.map((door) => (
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
    if (hash === "") {
      window.scrollTo({ top: 0 });
      return;
    }
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
            SILIP estimates the load on neighborhood transformers, from homes that opt in.
          </h1>
          <p className="max-w-xl text-muted-foreground">
            Grid engineers see which transformers may overload. Residents can check for outages right here.
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
