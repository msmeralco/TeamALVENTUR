import { Fragment, useEffect, useRef, type ReactNode, type RefObject } from "react";
import { Link, useLocation } from "react-router-dom";
import { LoadChart } from "../features/transformer-card/LoadChart";
import { useAuth, type Group } from "../shared/auth";
import { SimulatedLabel, TierBadge, formatPct } from "../shared/ui";
import { Button } from "../shared/ui/components/button";
import { Card } from "../shared/ui/components/card";
import { useDocumentTitle } from "../shared/ui/feedback";
import { EXAMPLE_TRANSFORMER } from "./engineerExample";
import { Decode, HUD_LABEL, HeroMap, LineDrawing } from "./LandingArt";

const SECTION = "grid scroll-mt-24 gap-6";

/** Each step: a short title and one sentence. */
const STEPS = [
  { label: "Household clamp", text: "A clamp on an opted-in home's wiring reads its power use, after the meter." },
  { label: "Summed per transformer", text: "Readings are added up per transformer, matched by a hashed Service ID." },
  { label: "Load and risk", text: "SILIP estimates the load and forecasts the next 24 hours." },
  { label: "Dashboard", text: "Engineers see which transformers may overload, with coverage and confidence." },
];

/** Dark stage. Wide screens with a mouse pin it while the drawing builds step by step; others reveal in place. */
function HowItWorks() {
  return (
    <section
      id="how-it-works"
      data-stage
      data-how
      aria-labelledby="how-it-works-title"
      // Wide screens: tucked under the hero's empty lower edge, with the steps near the top, so the
      // steps come into view as the map's HUD leaves.
      className="scroll-mt-16 bg-stage text-foreground lg:-mt-24"
    >
      <div className="mx-auto grid max-w-6xl items-center gap-10 px-4 py-20 sm:px-6 lg:min-h-[calc(100svh-4rem)] lg:grid-cols-2 lg:items-start lg:gap-16 lg:pt-28">
        <div className="grid gap-8">
          <h2 id="how-it-works-title" className="text-xl">
            How it works
          </h2>
          <ol className="grid gap-6">
            {STEPS.map((s, i) => (
              <li key={s.label} data-step className="grid grid-cols-[2.5rem_1fr] items-start gap-x-4">
                <span
                  aria-hidden="true"
                  className="grid size-10 place-items-center rounded-full border-2 border-brand font-display font-bold"
                >
                  {i + 1}
                </span>
                <div className="grid gap-1">
                  <h3 className="text-base font-semibold">
                    <Decode text={s.label} />
                  </h3>
                  <p className="text-sm text-muted-foreground">{s.text}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
        <LineDrawing />
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
      <Card data-example-card className="gap-5 px-4 shadow-none sm:px-6">
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
        <div data-example-chart>
          <LoadChart points={[...t.load]} ratedKva={t.rated_kva} nowLabel="Snapshot" />
        </div>
      </Card>
    </section>
  );
}

const PRIVACY = [
  "Households opt in. No clamp goes in without the owner's consent.",
  "Service IDs are stored only as salted hashes, never as plain numbers.",
  "SILIP never touches Meralco's meter, seal, service drop or transformer.",
];

function Privacy() {
  return (
    <section id="privacy" aria-labelledby="privacy-title" className={SECTION}>
      <h2 id="privacy-title" className="text-xl">
        Privacy, in plain words
      </h2>
      <ul data-privacy className="grid max-w-2xl list-disc gap-2 pl-5 marker:text-brand">
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
    open: "Open dashboard",
    group: "engineers",
  },
];

/** Signed out: the engineer door with Sign in. Signed in: the door only if it is the viewer's own view. */
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

function reducedMotion(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Loads the scroll motion after first paint, never with reduced motion; the page works without it. */
function useLandingMotion(root: RefObject<HTMLDivElement | null>) {
  useEffect(() => {
    if (reducedMotion() || root.current === null) return;
    const el = root.current;
    let stop: (() => void) | null = null;
    let cancelled = false;
    void import("./landingMotion").then(({ startLandingMotion }) => {
      if (!cancelled) stop = startLandingMotion(el);
    });
    return () => {
      cancelled = true;
      stop?.();
    };
  }, [root]);
}

const MAP_CREDIT = [
  { label: "OpenFreeMap", href: "https://openfreemap.org" },
  { label: "© OpenMapTiles", href: "https://www.openmaptiles.org/" },
  { label: "© OpenStreetMap contributors", href: "https://www.openstreetmap.org/copyright" },
];

/** The hero's one primary action: Sign in when signed out, the dashboard for engineers. */
function HeroAction() {
  const { user, signIn, hasGroup } = useAuth();
  if (user === null) {
    return (
      <Button className="min-h-11 w-fit rounded-full px-6" onClick={() => void signIn("/engineer")}>
        Sign in
      </Button>
    );
  }
  if (!hasGroup("engineers")) return null;
  return (
    <Button asChild className="min-h-11 w-fit rounded-full px-6">
      <Link to="/engineer">Open dashboard</Link>
    </Button>
  );
}

/** Dark, full screen: the risk map still, the headline and the one action, usable before any motion loads. */
function Hero() {
  return (
    <section
      data-stage
      data-hero
      aria-labelledby="hero-title"
      className="relative isolate grid min-h-[calc(100svh-4rem)] overflow-hidden bg-stage text-foreground max-sm:min-h-[calc(100svh-8rem)]"
    >
      <HeroMap />
      <div className="relative mx-auto grid w-full max-w-6xl content-between gap-5 px-4 pt-3 pb-4 sm:gap-8 sm:px-6 sm:pt-4 sm:pb-10">
        <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-2">
          {/* The HUD's title and legend: tier colors always come with their word. */}
          <div data-hud-label className="flex flex-wrap items-center gap-x-3 gap-y-2 text-sm font-semibold">
            <Decode text={HUD_LABEL} />
            <span className="flex gap-1">
              <TierBadge tier="Critical" />
              <TierBadge tier="OK" />
            </span>
          </div>
          {/* Foreground, not muted: muted text drops under 4.5:1 over the brightest parts of the map. */}
          <p className="flex flex-wrap items-center justify-end gap-x-2 gap-y-1 text-sm">
            <SimulatedLabel show />
            <span>
              Map{" "}
              {MAP_CREDIT.map((c, i) => (
                <Fragment key={c.href}>
                  {i > 0 && " "}
                  <a href={c.href} target="_blank" rel="noreferrer" className="underline underline-offset-4">
                    {c.label}
                  </a>
                </Fragment>
              ))}
            </span>
          </p>
        </div>
        <div data-hero-lift className="grid max-w-4xl gap-3 sm:gap-5">
          <h1 id="hero-title" className="text-display text-balance">
            See the load on the transformer that feeds your street.
          </h1>
          <p className="max-w-xl text-pretty">
            SILIP estimates it from homes that opt in, so grid engineers can see which transformers may overload in
            the next 24 hours.
          </p>
          <div className="pt-1 sm:pt-2">
            <HeroAction />
          </div>
        </div>
      </div>
    </section>
  );
}

/** A slim bracketed bar on the right edge that fills as you scroll. Decorative; only runs with motion. */
function ScrollProgress() {
  return (
    <div
      aria-hidden="true"
      data-scroll-progress
      className="pointer-events-none fixed top-1/2 right-3 z-10 hidden h-48 w-2 -translate-y-1/2 border-y-2 border-brand motion-safe:md:block"
    >
      <span className="absolute inset-y-1 left-1/2 w-px -translate-x-1/2 bg-brand/40" />
      <span
        data-fill
        className="absolute inset-y-1 left-1/2 w-0.5 origin-top -translate-x-1/2 bg-brand"
        style={{ transform: "scaleY(0)" }}
      />
    </div>
  );
}

/** Public landing page: the headline and Sign in first, then how it works, what engineers see, privacy and sign-in. */
export function LandingPage() {
  useDocumentTitle();
  useScrollToHash();
  const root = useRef<HTMLDivElement>(null);
  useLandingMotion(root);
  return (
    <div ref={root}>
      <Hero />
      <HowItWorks />
      <div data-curtain className="bg-background">
        <div className="mx-auto grid max-w-6xl gap-16 px-4 py-16 sm:gap-24 sm:px-6 sm:py-24">
          <EngineerPreview />
          <Privacy />
          <Doors />
        </div>
      </div>
      <ScrollProgress />
    </div>
  );
}
