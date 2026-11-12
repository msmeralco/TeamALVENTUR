import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { BrowserRouter, Link, NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { UsagePage } from "../features/household/UsagePage";
import { OutagesPage } from "../features/outages/OutagesPage";
import { RiskMapPage } from "../features/risk-map/RiskMapPage";
import { TransformerCardPage } from "../features/transformer-card/TransformerCardPage";
import { shouldRetry } from "../shared/api/client";
import { AuthProvider, RequireRole, takeReturnPath, useAuth, type AuthBackend, type Group } from "../shared/auth";
import { StateCard, cn } from "../shared/ui";
import { Button } from "../shared/ui/components/button";
import { Toaster } from "../shared/ui/components/sonner";
import { TooltipProvider } from "../shared/ui/components/tooltip";
import { OfflineBanner, RouteErrorBoundary, useDocumentTitle } from "../shared/ui/feedback";
import { AccountMenu } from "./AccountMenu";

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
        // If Cognito answers after the timeout, the user is signed in after all: finish the redirect.
        finishing.then(
          () => navigate(takeReturnPath(), { replace: true }),
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
    <StateCard title="Sign-in did not finish">
      <p className="text-sm text-muted-foreground">The sign-in page did not answer in time, or the link expired.</p>
      <Button className="mt-2 min-h-11 rounded-full" onClick={() => void signIn(takeReturnPath())}>
        Try again
      </Button>
      <Button asChild variant="outline" className="min-h-11 rounded-full">
        <Link to="/">Back to outages</Link>
      </Button>
    </StateCard>
  );
}

function NotFoundPage() {
  useDocumentTitle("Page not found");
  return (
    <StateCard title="Page not found">
      <p className="text-sm text-muted-foreground">This link may be old or mistyped.</p>
      <Button asChild variant="outline" className="mt-2 min-h-11 rounded-full">
        <Link to="/">See outages</Link>
      </Button>
    </StateCard>
  );
}

const NAV: { to: string; label: string; end: boolean; group?: Group }[] = [
  { to: "/", label: "Outages", end: true },
  { to: "/engineer", label: "Risk map", end: false, group: "engineers" },
  { to: "/me/usage", label: "My usage", end: false, group: "households" },
];

/** Pill links in the header on wide screens; a bottom tab bar on phones. Signed-in users see only their views. */
function MainNav() {
  const { user, hasGroup } = useAuth();
  const items = NAV.filter((item) => item.group === undefined || user === null || hasGroup(item.group));
  return (
    <nav
      aria-label="Main"
      className={cn(
        "flex gap-1",
        "max-sm:fixed max-sm:inset-x-0 max-sm:bottom-0 max-sm:z-20 max-sm:h-16 max-sm:gap-0 max-sm:border-t max-sm:bg-card max-sm:pb-[env(safe-area-inset-bottom)]",
      )}
    >
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          className={({ isActive }) =>
            cn(
              "rounded-full px-4 py-2 text-sm font-semibold text-muted-foreground no-underline transition-colors duration-150 hover:bg-accent hover:text-foreground",
              "max-sm:m-2 max-sm:grid max-sm:flex-1 max-sm:place-items-center",
              isActive && "bg-accent text-foreground",
            )
          }
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}

function Shell() {
  const location = useLocation();
  const { hasGroup } = useAuth();
  // The risk map is a full-screen map; every other page sits in the centered column.
  const fullBleed = location.pathname === "/engineer" && hasGroup("engineers");
  return (
    <>
      <a
        href="#main"
        className="sr-only rounded-full bg-card px-4 py-2 text-sm font-semibold focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50"
      >
        Skip to content
      </a>
      <header className="sticky top-0 z-20 border-b bg-card">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-4 sm:px-6">
          <Link to="/" className="font-display text-xl font-bold tracking-wider no-underline">
            SILIP
          </Link>
          <MainNav />
          <div className="ml-auto flex min-w-0 items-center gap-2">
            <AccountMenu />
          </div>
        </div>
        <OfflineBanner />
      </header>
      <main
        id="main"
        tabIndex={-1}
        className={cn(
          "outline-none",
          fullBleed ? "w-full" : "mx-auto max-w-6xl px-4 pt-6 pb-28 sm:px-6 sm:pt-10 sm:pb-20",
        )}
      >
        <RouteErrorBoundary key={location.pathname}>
          <Routes>
            <Route path="/" element={<OutagesPage />} />
            <Route
              path="/engineer"
              element={
                <RequireRole role="engineers">
                  <RiskMapPage />
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
            <Route
              path="/me/usage"
              element={
                <RequireRole role="households">
                  <UsagePage />
                </RequireRole>
              }
            />
            <Route path="/auth/callback" element={<AuthCallbackPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </RouteErrorBoundary>
      </main>
      <Toaster position="bottom-center" offset={88} mobileOffset={{ bottom: 88 }} />
    </>
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
