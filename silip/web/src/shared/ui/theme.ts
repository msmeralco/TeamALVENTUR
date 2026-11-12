import { useCallback, useEffect, useState, useSyncExternalStore } from "react";

export type ThemeChoice = "light" | "dark" | "system";

// A per-viewer convenience, so localStorage is fine here (sessions never go there).
const STORAGE_KEY = "silip.theme";
const DARK_QUERY = "(prefers-color-scheme: dark)";

function readChoice(): ThemeChoice {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return stored === "light" || stored === "dark" ? stored : "system";
  } catch {
    return "system";
  }
}

/** Sets data-theme on <html>; "system" removes it so tokens.css follows the OS. */
function applyChoice(choice: ThemeChoice) {
  const root = document.documentElement;
  if (choice === "system") delete root.dataset.theme;
  else root.dataset.theme = choice;
}

function systemIsDark(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia(DARK_QUERY).matches;
}

// One shared choice, so the header, footer and account menu toggles stay in step.
let current: ThemeChoice | null = null;
const listeners = new Set<() => void>();

function getChoice(): ThemeChoice {
  current ??= readChoice();
  return current;
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** The viewer's Light / Dark / System choice and the theme actually shown. */
export function useTheme() {
  const choice = useSyncExternalStore(subscribe, getChoice);
  const [systemDark, setSystemDark] = useState(systemIsDark);

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const media = window.matchMedia(DARK_QUERY);
    const onChange = () => setSystemDark(media.matches);
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  const setChoice = useCallback((next: ThemeChoice) => {
    applyChoice(next);
    current = next;
    try {
      if (next === "system") window.localStorage.removeItem(STORAGE_KEY);
      else window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Storage blocked (private mode): the choice still applies for this visit.
    }
    listeners.forEach((listener) => listener());
  }, []);

  const resolved: "light" | "dark" = choice === "system" ? (systemDark ? "dark" : "light") : choice;
  return { choice, resolved, setChoice };
}
