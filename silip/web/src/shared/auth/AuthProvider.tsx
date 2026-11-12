import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { setTokenSource } from "../api/client";
import type { AuthBackend, AuthUser, Group } from "./backend";

interface AuthContextValue {
  status: "loading" | "ready";
  user: AuthUser | null;
  hasGroup: (group: Group) => boolean;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
  completeSignIn: (url: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ backend, children }: { backend: AuthBackend; children: ReactNode }) {
  const [status, setStatus] = useState<"loading" | "ready">("loading");
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    void backend.load().then((loaded) => {
      setUser(loaded);
      setStatus("ready");
    });
  }, [backend]);

  useEffect(() => setTokenSource(() => user?.accessToken ?? null), [user]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      hasGroup: (group) => user?.groups.includes(group) ?? false,
      signIn: async () => setUser(await backend.signIn()),
      signOut: async () => {
        await backend.signOut();
        setUser(null);
      },
      completeSignIn: async (url) => setUser(await backend.completeSignIn(url)),
    }),
    [backend, status, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (value === null) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
