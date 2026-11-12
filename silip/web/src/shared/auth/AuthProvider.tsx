import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { setSessionEndedHandler, setTokenSource } from "../api/client";
import type { AuthBackend, AuthUser, Group } from "./backend";

// The page to come back to after the sign-in redirect. sessionStorage only: it is per tab and never outlives it.
const RETURN_TO_KEY = "silip.returnTo";

/** Accepts only same-origin app paths, so a stored value can never redirect off the site. */
function isSafePath(path: string | null): path is string {
  return (
    path !== null &&
    path.startsWith("/") &&
    !path.startsWith("//") &&
    !path.includes("\\") &&
    !path.startsWith("/auth/")
  );
}

/** Reads and clears the stored return path; "/" when there is none. */
export function takeReturnPath(): string {
  try {
    const path = window.sessionStorage.getItem(RETURN_TO_KEY);
    window.sessionStorage.removeItem(RETURN_TO_KEY);
    return isSafePath(path) ? path : "/";
  } catch {
    return "/";
  }
}

function rememberReturnPath(path: string) {
  try {
    if (isSafePath(path)) window.sessionStorage.setItem(RETURN_TO_KEY, path);
  } catch {
    // Storage blocked: sign-in still works and lands on "/".
  }
}

const currentPath = () => window.location.pathname + window.location.search;

interface AuthContextValue {
  status: "loading" | "ready";
  user: AuthUser | null;
  /** True after the API answered 401: the token expired or was revoked. */
  sessionEnded: boolean;
  hasGroup: (group: Group) => boolean;
  /** Signs in and comes back to `returnTo` (default: the current page). */
  signIn: (returnTo?: string) => Promise<void>;
  signOut: () => Promise<void>;
  completeSignIn: (url: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ backend, children }: { backend: AuthBackend; children: ReactNode }) {
  const [status, setStatus] = useState<"loading" | "ready">("loading");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [sessionEnded, setSessionEnded] = useState(false);

  useEffect(() => {
    void backend.load().then((loaded) => {
      setUser(loaded);
      setStatus("ready");
    });
  }, [backend]);

  useEffect(() => setTokenSource(() => user?.accessToken ?? null), [user]);
  useEffect(
    () =>
      setSessionEndedHandler(() => {
        setUser(null);
        setSessionEnded(true);
      }),
    [],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      sessionEnded,
      hasGroup: (group) => user?.groups.includes(group) ?? false,
      signIn: async (returnTo) => {
        rememberReturnPath(returnTo ?? currentPath());
        const signedIn = await backend.signIn();
        // Dev mode signs in without leaving the page, so the stored path is not needed.
        if (signedIn !== null) takeReturnPath();
        setUser(signedIn);
        setSessionEnded(false);
      },
      signOut: async () => {
        await backend.signOut();
        setUser(null);
        setSessionEnded(false);
      },
      completeSignIn: async (url) => {
        setUser(await backend.completeSignIn(url));
        setSessionEnded(false);
      },
    }),
    [backend, status, user, sessionEnded],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (value === null) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
