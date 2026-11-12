import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useSyncExternalStore } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../shared/auth";
import { ThemeToggle } from "../shared/ui/ThemeToggle";

const HEADING = "text-sm font-semibold text-foreground";
// Touch screens of any width get 44px rows; mouse sizes stay as they were.
const LINK =
  "text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline pointer-coarse:flex pointer-coarse:min-h-11 pointer-coarse:items-center";

function flagged(data: unknown): boolean {
  return typeof data === "object" && data !== null && "is_simulated" in data && data.is_simulated === true;
}

/**
 * True when the current page shows simulated data: a query in use on screen is marked is_simulated,
 * or the page is the landing page, whose engineer example is always simulated.
 */
function useShowsSimulated(): boolean {
  const { pathname } = useLocation();
  const cache = useQueryClient().getQueryCache();
  const subscribe = useCallback((onChange: () => void) => cache.subscribe(onChange), [cache]);
  const fromQueries = useSyncExternalStore(subscribe, () =>
    cache
      .findAll({ type: "active" })
      .some(({ state: { data } }) => (Array.isArray(data) ? data.some(flagged) : flagged(data))),
  );
  return fromQueries || pathname === "/";
}

export function Footer() {
  const { user, signIn } = useAuth();
  const simulated = useShowsSimulated();
  return (
    <footer className="border-t bg-card max-sm:pb-[calc(4rem+env(safe-area-inset-bottom))]">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-8 sm:px-6">
        <div className="grid gap-6 sm:grid-cols-3 sm:gap-8">
          <nav aria-labelledby="footer-product" className="grid content-start justify-items-start gap-2">
            <h2 id="footer-product" className={HEADING}>
              Product
            </h2>
            <Link to="/outages" className={LINK}>
              Outages
            </Link>
            <Link to="/#how-it-works" className={LINK}>
              How it works
            </Link>
            {user === null && (
              <button type="button" className={`${LINK} cursor-pointer`} onClick={() => void signIn()}>
                Sign in
              </button>
            )}
          </nav>
          <div className="grid content-start justify-items-start gap-2">
            <h2 className={HEADING}>About</h2>
            <p className="text-sm text-muted-foreground">Built by Alventur Solutions for the Meralco Idol Hackathon 2026.</p>
            {simulated && (
              <p className="text-sm text-muted-foreground">Items marked Simulated data use simulated readings.</p>
            )}
            <Link to="/sources" className={LINK}>
              Data sources
            </Link>
          </div>
          <div className="grid content-start justify-items-start gap-2">
            <h2 className={HEADING}>Theme</h2>
            {/* Pull the button left so its icon lines up with the text in the other groups. */}
            <div className="-my-1 -ml-3">
              <ThemeToggle withWord />
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 border-t pt-6 text-sm text-muted-foreground">
          <span className="grid size-7 place-items-center rounded-md bg-logo-tile">
            <img src="/brand/silip-mark-128.png" alt="" width={24} height={24} className="size-6" />
          </span>
          <span className="font-display font-bold text-foreground">silip</span>
          <span>{new Date().getFullYear()}</span>
        </div>
      </div>
    </footer>
  );
}
