import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useSyncExternalStore } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../shared/auth";
import { ThemeToggle } from "../shared/ui/ThemeToggle";

const LINK = "text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline";

function flagged(data: unknown): boolean {
  return typeof data === "object" && data !== null && "is_simulated" in data && data.is_simulated === true;
}

/** True once any loaded API answer is marked is_simulated, the only global signal the API gives. */
function useShowsSimulated(): boolean {
  const cache = useQueryClient().getQueryCache();
  const subscribe = useCallback((onChange: () => void) => cache.subscribe(onChange), [cache]);
  return useSyncExternalStore(subscribe, () =>
    cache.getAll().some(({ state: { data } }) => (Array.isArray(data) ? data.some(flagged) : flagged(data))),
  );
}

export function Footer() {
  const { user, signIn } = useAuth();
  const simulated = useShowsSimulated();
  return (
    <footer className="border-t bg-card max-sm:pb-[calc(4rem+env(safe-area-inset-bottom))]">
      <div className="mx-auto grid max-w-6xl gap-6 px-4 py-8 sm:grid-cols-3 sm:px-6">
        <nav aria-label="Footer" className="grid content-start gap-2">
          <Link to="/outages" className={LINK}>
            Outages
          </Link>
          <Link to="/#how-it-works" className={LINK}>
            How it works
          </Link>
          {user === null && (
            <button type="button" className={`${LINK} w-fit cursor-pointer`} onClick={() => void signIn()}>
              Sign in
            </button>
          )}
        </nav>
        <div className="grid content-start gap-2">
          <p className="text-sm text-muted-foreground">Built by Alventur Solutions for the Meralco Idol Hackathon 2026.</p>
          <Link to="/sources" className={LINK}>
            Data sources
          </Link>
        </div>
        <div className="grid content-start justify-items-start gap-2">
          {simulated && (
            <p className="text-sm text-muted-foreground">Readings shown are simulated unless marked otherwise.</p>
          )}
          <ThemeToggle />
        </div>
      </div>
      <div className="mx-auto flex max-w-6xl items-center gap-2 px-4 pb-8 text-sm text-muted-foreground sm:px-6">
        <span className="grid size-7 place-items-center rounded-md bg-logo-tile">
          <img src="/brand/silip-mark-128.png" alt="" width={24} height={24} className="size-6" />
        </span>
        <span className="font-display font-bold text-foreground">silip</span>
        <span>{new Date().getFullYear()}</span>
      </div>
    </footer>
  );
}
