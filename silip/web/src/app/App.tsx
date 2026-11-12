import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Cpu, House, Info, LayoutDashboard, type LucideIcon } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { DemoPage } from "../features/demo/DemoPage";
import { DevicesPage } from "../features/devices/DevicesPage";
import { DashboardPage } from "../features/dashboard/DashboardPage";
import { TransformerCardPage } from "../features/transformer-card/TransformerCardPage";
import { shouldRetry } from "../shared/api/client";
import { AuthProvider, RequireRole, takeReturnPath, useAuth, type AuthBackend, type Group } from "../shared/auth";
import { StateCard, cn } from "../shared/ui";
import { Button } from "../shared/ui/components/button";
import { Toaster } from "../shared/ui/components/sonner";
import { TooltipProvider } from "../shared/ui/components/tooltip";
import { OfflineBanner, RouteErrorBoundary, useDocumentTitle } from "../shared/ui/feedback";
import { AccountMenu } from "./AccountMenu";
import { Footer } from "./Footer";
import { LandingPage } from "./LandingPage";
import { SourcesPage } from "./SourcesPage";
import { useHeaderOverStage, useMediaQuery } from "./useHeaderOverStage";

// Cognito normally answers in a second or two; past this, assume the redirect broke. [VERIFY] on slow networks.
const CALLBACK_TIMEOUT_MS = 15_000;

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => reject(new Error("Sign-in timed out")), ms);
    promise.then(
      (value) => {
        window.clearTimeout(timer);
        resolve(value);
      },
      (error: unknown) => {
        window.clearTimeout(timer);
        reject(error);
      },
    );
  });
}

function AuthCallbackPage() {
  useDocumentTitle("Signing in");
  const { completeSignIn, signIn } = useAuth();
  const navigate = useNavigate();
  const [failed, setFailed] = useState(false);
  const started = useRef(false);
  useEffect(() => {
    // The code in the URL works once; StrictMode runs effects twice in dev.
    if (started.current) return;
    started.current = true;
    const finishing = completeSignIn(window.location.href);
    withTimeout(finishing, CALLBACK_TIMEOUT_MS).then(
      () => navigate(takeReturnPath(), { replace: true }),
      (error: unknown) => {
        console.warn("Sign-in callback failed", error);
        setFailed(true);
        // If Cognito answers after the timeout, the user is signed in after all: finish the redirect,
        // unless they already left this page from the timeout card.
        finishing.then(
          () => {
            if (window.location.pathname === "/auth/callback") navigate(takeReturnPath(), { replace: true });
          },
          () => {},
        );
      },
    );
  }, [completeSignIn, navigate]);

  if (!failed) {
    return (
      <p role="status" className="mt-10 text-center text-sm text-muted-foreground">
        Signing you in…
      </p>
    );
  }
  return (
    <StateCard
      role="alert"
      title="Sign-in did not finish"
      actions={
        <>
          <Button className="min-h-11 rounded-full" onClick={() => void signIn(takeReturnPath())}>
            Try again
          </Button>
          <Button asChild variant="outline" className="min-h-11 rounded-full">
            <Link to="/">Back to home</Link>
          </Button>
        </>
      }
    >
      <p className="text-sm text-muted-foreground">The sign-in page did not answer in time, or the link expired.</p>
    </StateCard>
  );
}

interface NotFoundLink {
  to: string;
  label: string;
}

/** Home for everyone; engineers also get the dashboard, which then becomes the one primary button. */
function NotFoundPage() {
  useDocumentTitle("Page not found");
  const { hasGroup } = useAuth();
  const links: NotFoundLink[] = [
    ...(hasGroup("engineers") ? [{ to: "/engineer", label: "Dashboard" }] : []),
    { to: "/", label: "Home" },
  ];
  return (
    <StateCard
      title="Page not found"
      actions={links.map((link, i) => (
        // The key includes the role so a button that changes variant once sign-in loads is replaced, not faded.
        <Button
          key={`${link.to}:${i}`}
          asChild
          variant={i === 0 ? "default" : "outline"}
          className="min-h-11 rounded-full"
        >
          <Link to={link.to}>{link.label}</Link>
        </Button>
      ))}
    >
      <p className="text-sm text-muted-foreground">This link may be old or mistyped.</p>
    </StateCard>
  );
}

interface NavItem {
  to: string;
  label: string;
  /** Shown under the icon on phones when the full label would wrap. */
  short?: string;
  icon: LucideIcon;
  group?: Group;
}

const PUBLIC_NAV: NavItem[] = [
  { to: "/", label: "Home", icon: House },
  { to: "/#how-it-works", label: "How it works", icon: Info },
];

// Signed in as an engineer: the engineer views. Anyone else gets the public nav.
const MEMBER_NAV: NavItem[] = [
  { to: "/engineer", label: "Dashboard", icon: LayoutDashboard, group: "engineers" },
  { to: "/engineer/devices", label: "Devices", icon: Cpu, group: "engineers" },
];

function isCurrent(to: string, pathname: string, hash: string): boolean {
  const [path, anchor] = to.split("#");
  if (path !== pathname) return false;
  // Home and its "How it works" anchor share "/", so the hash decides which one is current.
  return anchor === undefined ? hash !== "#how-it-works" : hash === `#${anchor}`;
}

/** Pill links in the header on wide screens; a bottom tab bar with icons on phones. */
function MainNav({ onStage }: { onStage: boolean }) {
  const { user, hasGroup } = useAuth();
  const { pathname, hash } = useLocation();
  // On phones the nav is the bottom tab bar, far from the stage, so it keeps the page colors.
  const inHeader = useMediaQuery("(min-width: 40rem)");
  const member =
    user === null ? [] : MEMBER_NAV.filter((item) => item.group === undefined || hasGroup(item.group));
  const items = member.length > 0 ? member : PUBLIC_NAV;
  return (
    <nav
      aria-label="Main"
      data-stage={onStage && inHeader ? "" : undefined}
      className={cn(
        "flex gap-1",
        "max-sm:fixed max-sm:inset-x-0 max-sm:bottom-0 max-sm:z-20 max-sm:box-content max-sm:h-16 max-sm:gap-0 max-sm:border-t max-sm:bg-card max-sm:px-1 max-sm:pb-[env(safe-area-inset-bottom)]",
      )}
    >
      {items.map((item) => {
        const current = isCurrent(item.to, pathname, hash);
        const Icon = item.icon;
        return (
          <Link
            key={item.to}
            to={item.to}
            aria-current={current ? (item.to.includes("#") ? "location" : "page") : undefined}
            aria-label={item.short === undefined ? undefined : item.label}
            className={cn(
              "rounded-full px-3 py-2 text-sm font-semibold whitespace-nowrap text-muted-foreground no-underline transition-colors duration-150 hover:bg-accent hover:text-foreground pointer-coarse:flex pointer-coarse:min-h-11 pointer-coarse:items-center lg:px-4",
              "max-sm:my-1.5 max-sm:flex max-sm:min-h-11 max-sm:min-w-0 max-sm:flex-1 max-sm:flex-col max-sm:items-center max-sm:justify-center max-sm:gap-0.5 max-sm:rounded-xl max-sm:px-1 max-sm:py-1 max-sm:text-xs",
              current && "bg-selected text-selected-foreground hover:bg-selected hover:text-selected-foreground",
            )}
          >
            <Icon aria-hidden="true" className="size-5 sm:hidden" />
            {item.short === undefined ? (
              item.label
            ) : (
              <>
                <span className="sm:hidden">{item.short}</span>
                <span className="max-sm:hidden">{item.label}</span>
              </>
            )}
          </Link>
        );
      })}
    </nav>
  );
}

/** The outage and household views are gone; their old links go to the dashboard for engineers, else home. */
function RetiredRoute() {
  const { status, hasGroup } = useAuth();
  if (status === "loading") return null;
  return <Navigate to={hasGroup("engineers") ? "/engineer" : "/"} replace />;
}

function Shell() {
  const location = useLocation();
  const { hasGroup } = useAuth();
  // The dashboard and the landing page are full width; every other page sits in the centered column.
  const fullBleed = (location.pathname === "/engineer" && hasGroup("engineers")) || location.pathname === "/";
  const header = useRef<HTMLElement>(null);
  const onStage = useHeaderOverStage(header, location.pathname === "/");
  // Over the landing page's dark stage the header takes the stage color and its dark tokens.
  const stage = onStage ? "" : undefined;
  return (
    // A full-height column, so the footer sits at the bottom of short pages such as the 404.
    <div className="flex min-h-dvh flex-col">
      <a
        href="#main"
        className="sr-only rounded-full bg-card px-4 py-2 text-sm font-semibold focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50"
      >
        Skip to content
      </a>
      <header
        ref={header}
        data-over-stage={stage}
        className={cn(
          "sticky top-0 z-20 border-b transition-colors duration-150",
          onStage ? "border-transparent bg-stage" : "bg-card",
        )}
      >
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4 sm:px-6 lg:gap-6">
          <Link
            to="/"
            aria-label="SILIP home"
            data-stage={stage}
            className="flex shrink-0 items-center gap-2 font-display text-xl font-bold text-foreground no-underline"
          >
            {/* The logo's navy lid vanishes on dark surfaces, so dark mode puts the mark on a cream tile. */}
            <span className="grid size-9 place-items-center rounded-lg bg-logo-tile">
              <img src="/brand/silip-mark-128.png" alt="" width={32} height={32} className="size-8" />
            </span>
            silip
          </Link>
          <MainNav onStage={onStage} />
          <div data-stage={stage} className="ml-auto flex min-w-0 items-center gap-2 text-foreground">
            <AccountMenu />
          </div>
        </div>
        <OfflineBanner />
      </header>
      <main
        id="main"
        tabIndex={-1}
        className={cn(
          "w-full flex-1 outline-none",
          fullBleed ? "" : "mx-auto max-w-6xl px-4 pt-6 pb-10 sm:px-6 sm:pt-10 sm:pb-16",
        )}
      >
        <RouteErrorBoundary key={location.pathname}>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/outages" element={<RetiredRoute />} />
            <Route path="/me/usage" element={<RetiredRoute />} />
            <Route
              path="/engineer"
              element={
                <RequireRole role="engineers">
                  <DashboardPage />
                </RequireRole>
              }
            />
            <Route
              path="/engineer/transformers/:transformerId"
              element={
                <RequireRole role="engineers">
                  <TransformerCardPage />
                </RequireRole>
              }
            />
            <Route path="/demo" element={<DemoPage />} />
            <Route path="/sources" element={<SourcesPage />} />
            <Route
              path="/engineer/devices"
              element={
                <RequireRole role="engineers">
                  <DevicesPage />
                </RequireRole>
              }
            />
            <Route path="/auth/callback" element={<AuthCallbackPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </RouteErrorBoundary>
      </main>
      <Footer />
      <Toaster position="bottom-center" offset={88} mobileOffset={{ bottom: 88 }} />
    </div>
  );
}

export function App({ backend }: { backend: AuthBackend }) {
  const queryClient = useMemo(() => new QueryClient({ defaultOptions: { queries: { retry: shouldRetry } } }), []);
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider backend={backend}>
        <TooltipProvider delayDuration={300}>
          <BrowserRouter>
            <Shell />
          </BrowserRouter>
        </TooltipProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
