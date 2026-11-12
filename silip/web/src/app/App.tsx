import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { BrowserRouter, Link, Navigate, Route, Routes } from "react-router-dom";
import { UsagePage } from "../features/household/UsagePage";
import { OutagesPage } from "../features/outages/OutagesPage";
import { RiskMapPage } from "../features/risk-map/RiskMapPage";
import { TransformerCardPage } from "../features/transformer-card/TransformerCardPage";
import { AuthProvider, RequireRole, useAuth, type AuthBackend } from "../shared/auth";

function AuthCallbackPage() {
  const { completeSignIn } = useAuth();
  const [done, setDone] = useState(false);
  useEffect(() => {
    void completeSignIn(window.location.href).then(() => setDone(true));
  }, [completeSignIn]);
  return done ? <Navigate to="/" replace /> : <p className="muted">Signing you in…</p>;
}

function Shell() {
  const { user, signIn, signOut } = useAuth();
  return (
    <>
      <header>
        <main style={{ display: "flex", gap: "1rem", alignItems: "center", flexWrap: "wrap" }}>
          <strong>SILIP</strong>
          <Link to="/">Outages</Link>
          <Link to="/engineer">Risk map</Link>
          <Link to="/me/usage">My usage</Link>
          <span style={{ marginLeft: "auto" }}>
            {user ? (
              <button onClick={() => void signOut()}>Sign out {user.username}</button>
            ) : (
              <button onClick={() => void signIn()}>Sign in</button>
            )}
          </span>
        </main>
      </header>
      <main>
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
          <Route path="*" element={<p>Page not found.</p>} />
        </Routes>
      </main>
    </>
  );
}

export function App({ backend }: { backend: AuthBackend }) {
  const queryClient = useMemo(() => new QueryClient({ defaultOptions: { queries: { retry: 1 } } }), []);
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider backend={backend}>
        <BrowserRouter>
          <Shell />
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
