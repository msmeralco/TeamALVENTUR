import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { createDevBackend, devUser, takeReturnPath, type AuthBackend } from "../shared/auth";
import { matchesId, normalizeId, reportAge } from "../shared/risk";

// MapLibre needs WebGL, which jsdom lacks; the list beside the map carries the same data.
vi.mock("../features/dashboard/TransformerMap", () => ({ TransformerMap: () => null }));
vi.mock("../features/devices/InstallationMap", () => ({ InstallationMap: () => null }));
// The landing scroll motion (GSAP, Lenis) is loaded lazily; tests check what renders without it.
const startLandingMotion = vi.hoisted(() => vi.fn((_root: HTMLElement) => () => {}));
vi.mock("./landingMotion", () => ({ startLandingMotion }));

type Action = "Inspect before peak" | "Add clamps" | "Fix clamps" | "Plan upgrade" | "Monitor";

function risk(id: string, tier: "OK" | "Watch" | "Critical", peak: number, action: Action | null = null) {
  return {
    action,
    transformer_id: id,
    lat: 14.58,
    lon: 121.0,
    rated_kva: 50,
    is_simulated: true,
    risk: {
      transformer_id: id,
      tier,
      reasons: [`Reason for ${id}`],
      confidence: 0.7,
      peak_load_pct: peak,
      coverage_pct: 0.4,
      is_simulated: true,
    },
  };
}

const LIST = [
  risk("T-1", "OK", 0.5, "Monitor"),
  risk("T-2", "Critical", 1.2, "Inspect before peak"),
  risk("T-3", "Watch", 0.95, "Add clamps"),
];

const NO_EV = { stations_within: 0, nearest_station_m: null, radius_m: 1000, stations: [], adoption_scenario: null };

/** A full transformer card payload; `extra` overrides any field. */
function card(id: string, tier: "OK" | "Watch" | "Critical", peak: number, extra: Record<string, unknown> = {}) {
  return {
    ...risk(id, tier, peak),
    as_of: "2026-04-30T20:15:00+08:00",
    load: LOAD,
    drivers: [],
    weather: [],
    ev: NO_EV,
    clamp_health: null,
    clamps_to_target: null,
    ...extra,
  };
}

const SUMMARY = {
  as_of: "2026-04-30T23:45:00+08:00",
  scored_at: "2026-05-01T00:05:00+08:00",
  tiers: { OK: 1, Watch: 1, Critical: 1 },
  actions: { "Inspect before peak": 1, "Add clamps": 1, Monitor: 1 },
  weather: { issued_at: "2026-04-30T00:00:00+08:00", status: "stale", source: "Simulated", heat_index_max_c: null, max_at: null },
  clamps: { installed: 10, online: 9 },
  model: { forecaster: "seasonal_naive", risk_scorer: "rules", kept: null },
  is_simulated: true,
};

function outlook(status: "fresh" | "stale" | "missing", hours: unknown[] = []) {
  return {
    issued_at: status === "missing" ? null : "2026-04-30T00:00:00+08:00",
    status,
    source: status === "fresh" ? "Open-Meteo" : "Simulated",
    hours,
    cells: [],
    is_simulated: status !== "fresh",
  };
}
const LOAD = [
  { ts: "2026-04-30T20:00:00+08:00", kw: 20, load_pct: 0.5, is_forecast: false },
  { ts: "2026-04-30T20:15:00+08:00", kw: 36, load_pct: 0.8, is_forecast: false },
  { ts: "2026-04-30T20:30:00+08:00", kw: 50, load_pct: 1.1, is_forecast: true },
  { ts: "2026-04-30T20:45:00+08:00", kw: 40, load_pct: 0.9, is_forecast: true },
];

/** Answers by path: "/api/v1/transformers" etc. A number answer is an error status. */
function mockApi(routes: Record<string, unknown>, status = 200) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (request: Request) => {
      const path = new URL(request.url).pathname;
      const body = routes[path] ?? { detail: "Not found" };
      const code = path in routes ? status : 404;
      return new Response(JSON.stringify(body), { status: code, headers: { "Content-Type": "application/json" } });
    }),
  );
}

function renderAt(path: string, backend: AuthBackend = createDevBackend()) {
  window.history.pushState({}, "", path);
  return render(<App backend={backend} />);
}

afterEach(() => vi.unstubAllGlobals());

describe("landing page", () => {
  it("opens on the headline and Sign in, then How it works and the labeled engineer example", async () => {
    mockApi({});
    renderAt("/", { ...createDevBackend(), load: async () => null });
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe(
      "See the load on the transformer that feeds your street.",
    );
    const hero = screen.getByRole("region", { name: "See the load on the transformer that feeds your street." });
    expect(await within(hero).findByRole("button", { name: "Sign in" })).toBeTruthy();
    expect(within(hero).getAllByText("Simulated data").length).toBeGreaterThan(0);
    expect(within(hero).getByRole("link", { name: "© OpenStreetMap contributors" })).toBeTruthy();
    expect(within(hero).queryByRole("button", { name: "Near me" })).toBeNull();
    expect(document.getElementById("how-it-works")?.querySelector("h2")?.textContent).toBe("How it works");
    expect(screen.getByText("Example")).toBeTruthy();
    expect(screen.getByText("Snapshot")).toBeTruthy();
    expect(screen.queryByText("Now")).toBeNull();
    expect(screen.queryByText(/household sees|For households|outages/i)).toBeNull();
    expect(document.title).toBe("SILIP");
  });

  it("gives engineers Open dashboard as the hero's primary action", async () => {
    mockApi({});
    renderAt("/");
    const hero = screen.getByRole("region", { name: "See the load on the transformer that feeds your street." });
    expect((await within(hero).findByRole("link", { name: "Open dashboard" })).getAttribute("href")).toBe("/engineer");
  });

  it("loads the scroll motion only when reduced motion is off", async () => {
    startLandingMotion.mockClear();
    mockApi({});
    renderAt("/");
    await waitFor(() => expect(startLandingMotion).toHaveBeenCalledTimes(1));
    expect(startLandingMotion).toHaveBeenCalledWith(document.querySelector("main > div"));
  });

  it("renders every section in its final state with reduced motion, and never loads the motion", async () => {
    startLandingMotion.mockClear();
    const matchMedia = window.matchMedia;
    window.matchMedia = (query: string) =>
      ({ ...matchMedia(query), matches: query.includes("min-width") || query.includes("reduce") }) as MediaQueryList;
    try {
      mockApi({});
      renderAt("/");
      expect((await screen.findAllByRole("link", { name: "Open dashboard" })).length).toBeGreaterThan(0);
      // Every decoding label shows its real text, and nothing is left hidden or offset by inline styles.
      for (const label of ["Transformer risk, next 24 h", "Household clamp", "Summed per transformer", "Load and risk", "Dashboard"]) {
        const shown = [...document.querySelectorAll<HTMLElement>("[data-decode]")].find((el) => el.dataset.decode === label);
        expect(shown?.textContent).toBe(label);
      }
      expect(screen.getByText("Critical · T-132")).toBeTruthy();
      for (const id of ["how-it-works", "engineers", "privacy", "sign-in"]) expect(document.getElementById(id)).toBeTruthy();
      expect(document.querySelectorAll("[data-privacy] li")).toHaveLength(3);
      expect(document.querySelector("[data-wordmark]")?.textContent).toBe("silip");
      expect(document.querySelector('main [style*="opacity"], main [style*="clip-path"]')).toBeNull();
      expect(startLandingMotion).not.toHaveBeenCalled();
    } finally {
      window.matchMedia = matchMedia;
    }
  });

  it("sends the retired /outages and /me/usage links home, or to the dashboard for engineers", async () => {
    mockApi({ "/api/v1/transformers": LIST });
    for (const path of ["/outages", "/me/usage"]) {
      const visitor = renderAt(path, { ...createDevBackend(), load: async () => null });
      await waitFor(() => expect(window.location.pathname).toBe("/"));
      visitor.unmount();
      const engineer = renderAt(path);
      await waitFor(() => expect(window.location.pathname).toBe("/engineer"));
      engineer.unmount();
    }
  });

  it("gives the header the stage color only while a stage section is under it, and only on /", async () => {
    const observers: { callback: IntersectionObserverCallback; targets: Element[] }[] = [];
    vi.stubGlobal(
      "IntersectionObserver",
      class {
        targets: Element[] = [];
        constructor(callback: IntersectionObserverCallback) {
          observers.push({ callback, targets: this.targets });
        }
        observe(el: Element) {
          this.targets.push(el);
        }
        disconnect() {}
      },
    );
    mockApi({ "/api/v1/transformers": LIST });
    renderAt("/");
    const header = screen.getAllByRole("banner")[0];
    const cross = (isIntersecting: boolean) =>
      act(() => {
        const { callback, targets } = observers[observers.length - 1];
        callback(targets.map((target) => ({ target, isIntersecting }) as IntersectionObserverEntry), {} as IntersectionObserver);
      });
    await waitFor(() => expect(observers.length).toBeGreaterThan(0));
    expect(observers[observers.length - 1].targets.every((t) => t.hasAttribute("data-stage"))).toBe(true);
    cross(true);
    expect(header.hasAttribute("data-over-stage")).toBe(true);
    expect(within(header).getByRole("link", { name: "SILIP home" }).hasAttribute("data-stage")).toBe(true);
    cross(false);
    expect(header.hasAttribute("data-over-stage")).toBe(false);
    cross(true);
    await userEvent.click(within(header).getAllByRole("link", { name: "Dashboard" })[0]);
    await waitFor(() => expect(window.location.pathname).toBe("/engineer"));
    expect(header.hasAttribute("data-over-stage")).toBe(false);
  });

  it("scrolls to How it works when the link carries its anchor", async () => {
    mockApi({});
    const scroll = vi.spyOn(Element.prototype, "scrollIntoView");
    renderAt("/#how-it-works");
    await waitFor(() => expect(scroll).toHaveBeenCalled());
    expect(scroll.mock.contexts[0]).toBe(document.getElementById("how-it-works"));
    scroll.mockRestore();
  });
});

describe("engineer dashboard queue", () => {
  it("ranks by action, Inspect before peak first, with Monitor behind a button", async () => {
    mockApi({
      "/api/v1/transformers": [
        risk("T-5", "Watch", 0.9, "Monitor"),
        risk("T-6", "Watch", 1.05, "Plan upgrade"),
        risk("T-7", "Watch", 0.95, "Fix clamps"),
        risk("T-8", "Critical", 2.1, "Add clamps"),
        risk("T-9", "Critical", 1.3, "Inspect before peak"),
        risk("T-10", "Critical", 1.6, "Inspect before peak"),
      ],
    });
    renderAt("/engineer");
    await screen.findByText("T-9");
    const queue = screen.getByRole("list", { name: "Action queue, most urgent first" });
    const ids = () => within(queue).getAllByRole("heading", { level: 3 }).map((h) => h.textContent);
    expect(ids()).toEqual(["T-10", "T-9", "T-8", "T-7", "T-6"]);
    await userEvent.click(screen.getByRole("button", { name: "Show 1 to monitor" }));
    expect(ids()).toEqual(["T-10", "T-9", "T-8", "T-7", "T-6", "T-5"]);
  });

  it("puts tier and action words, peak, reason, coverage and confidence on each row", async () => {
    mockApi({
      "/api/v1/transformers": [
        {
          ...risk("T-2", "Critical", 1.62, "Inspect before peak"),
          peak_ts: "2026-05-01T20:30:00+08:00",
          top_reason: "Peak forecast 162% of rating at 20:30",
          risk: {
            ...risk("T-2", "Critical", 1.62).risk,
            reasons: ["Peak forecast 162% of rating at 20:30", "Above 100% of rating for 6.0 h in a row"],
          },
        },
        risk("T-3", "Watch", 0.95, "Add clamps"),
      ],
    });
    renderAt("/engineer");
    const row = (await screen.findByText("T-2")).closest("li") as HTMLElement;
    expect(within(row).getByText("Critical")).toBeTruthy();
    expect(within(row).getByText("Inspect before peak")).toBeTruthy();
    expect(within(row).getByText(/^Peak 162% at /)).toBeTruthy();
    // The top reason only repeats the peak, so the row shows the next one.
    expect(within(row).getByText("Above 100% of rating for 6.0 h in a row")).toBeTruthy();
    expect(within(row).getByText("Coverage 40% | Confidence 70%")).toBeTruthy();
    const other = screen.getByText("T-3").closest("li") as HTMLElement;
    expect(within(other).getByText("Add clamps")).toBeTruthy();
    expect(within(other).getByText("Watch")).toBeTruthy();
  });

  it("shows the summary row with Simulated data, data time, weather freshness and model", async () => {
    mockApi({ "/api/v1/transformers": LIST, "/api/v1/dashboard/summary": SUMMARY });
    renderAt("/engineer");
    const summary = (await screen.findByRole("heading", { level: 1, name: "Dashboard" })).closest("header") as HTMLElement;
    expect(await within(summary).findByText("Simulated data")).toBeTruthy();
    expect(within(summary).getByText("Data as of")).toBeTruthy();
    expect(within(summary).getByText("Weather stale")).toBeTruthy();
    expect(within(summary).getByText(/Source: Simulated/)).toBeTruthy();
    expect(within(summary).getByText("seasonal naive forecast, rules risk scorer")).toBeTruthy();
    expect(document.title).toBe("Dashboard · SILIP");
  });

  it("says the summary is unavailable, with Try again, when it fails", async () => {
    mockApi({ "/api/v1/transformers": LIST });
    renderAt("/engineer");
    expect(await screen.findByText("Summary unavailable.")).toBeTruthy();
  });

  it("shows the empty and error states for the queue", async () => {
    mockApi({ "/api/v1/transformers": [] });
    const empty = renderAt("/engineer");
    expect(await screen.findByText("No transformers in this area.")).toBeTruthy();
    empty.unmount();
    mockApi({ "/api/v1/transformers": { detail: "Database unavailable" } }, 503);
    renderAt("/engineer");
    expect(await screen.findByText("Could not load this view", {}, { timeout: 5000 })).toBeTruthy();
  });

  it("shows a loading state before the queue arrives", async () => {
    // The API never answers, so the queue stays in its loading state.
    vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>(() => {})));
    renderAt("/engineer");
    await waitFor(() => expect(screen.getAllByText("Loading…").length).toBeGreaterThan(0));
    expect(screen.getByRole("heading", { name: "Action queue" })).toBeTruthy();
  });

  it("switches the map overlay one at a time, and loads DOE chargers only for the EV overlay", async () => {
    mockApi({
      "/api/v1/transformers": LIST,
      "/api/v1/ev/chargers": { radius_m: 1000, source: "DOE", stations: [], is_simulated: false },
    });
    renderAt("/engineer");
    await screen.findByText("T-2");
    const group = await screen.findByRole("radiogroup", { name: "Map overlay" });
    const radio = (name: string) => within(group).getByRole("radio", { name });
    expect(radio("Risk").getAttribute("aria-checked")).toBe("true");
    const fetched = () =>
      vi.mocked(fetch).mock.calls.some(([request]) => new URL((request as Request).url).pathname === "/api/v1/ev/chargers");
    expect(fetched()).toBe(false);
    await userEvent.click(radio("EV chargers"));
    expect(radio("EV chargers").getAttribute("aria-checked")).toBe("true");
    expect(radio("Risk").getAttribute("aria-checked")).toBe("false");
    await waitFor(() => expect(fetched()).toBe(true));
    await userEvent.click(radio("Clamp coverage"));
    expect(radio("Clamp coverage").getAttribute("aria-checked")).toBe("true");
    expect(radio("EV chargers").getAttribute("aria-checked")).toBe("false");
  });

  it("filters by tier with the filter kept in the URL", async () => {
    mockApi({ "/api/v1/transformers": LIST });
    renderAt("/engineer");
    await screen.findByText("T-2");
    await userEvent.click(screen.getByRole("button", { name: /^Critical 1$/ }));
    expect(window.location.search).toBe("?tier=Critical");
    expect(screen.getByRole("button", { name: /^Critical 1$/ }).getAttribute("aria-pressed")).toBe("true");
    expect(screen.queryByText("T-3")).toBeNull();
  });

  it("reads the tier filter from the URL on load", async () => {
    mockApi({ "/api/v1/transformers": LIST });
    renderAt("/engineer?tier=Watch");
    expect(await screen.findByText("T-3")).toBeTruthy();
    expect(screen.queryByText("T-2")).toBeNull();
  });

  it("finds a transformer by ID typed loosely", async () => {
    mockApi({ "/api/v1/transformers": LIST });
    renderAt("/engineer");
    await screen.findByText("T-2");
    await userEvent.type(screen.getByRole("searchbox", { name: "Find a transformer by ID" }), "t 3");
    expect(screen.getByText("T-3")).toBeTruthy();
    expect(screen.queryByText("T-2")).toBeNull();
  });

  it("shows an empty state with Clear filter when nothing matches", async () => {
    mockApi({ "/api/v1/transformers": LIST });
    renderAt("/engineer?q=999");
    expect(await screen.findByText("No transformers match this filter.")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "Clear filter" }));
    expect(await screen.findByText("T-2")).toBeTruthy();
  });

  it("asks to sign in again when the API says the session ended", async () => {
    mockApi({ "/api/v1/transformers": { detail: "Sign in required" } }, 401);
    renderAt("/engineer");
    expect(await screen.findByText("Your session ended")).toBeTruthy();
    expect(within(screen.getByRole("main")).getByRole("button", { name: "Sign in" })).toBeTruthy();
    expect(screen.queryByText("Could not load this view")).toBeNull();
  });
});

describe("weather strip", () => {
  it("says the forecast is stale in words, with its source", async () => {
    mockApi({ "/api/v1/transformers": LIST, "/api/v1/weather/outlook": outlook("stale") });
    renderAt("/engineer");
    const strip = (await screen.findByRole("heading", { name: "Heat index, next 48 h" })).closest("section") as HTMLElement;
    expect(await within(strip).findByText(/^The weather forecast is stale\. Last issued /)).toBeTruthy();
    expect(within(strip).getByText("Weather stale")).toBeTruthy();
    expect(within(strip).getByText("Source: Simulated")).toBeTruthy();
    expect(within(strip).getByText("No forecast hours to show.")).toBeTruthy();
  });

  it("says when no forecast is available", async () => {
    mockApi({ "/api/v1/transformers": LIST, "/api/v1/weather/outlook": outlook("missing") });
    renderAt("/engineer");
    expect(await screen.findByText("No weather forecast is available.")).toBeTruthy();
    expect(screen.getByText("Weather missing")).toBeTruthy();
  });

  it("draws the heat index with each Critical peak marked, and rain only when it rains", async () => {
    const hours = [0, 1, 2, 3].map((h) => ({
      ts: `2026-05-01T${String(18 + h).padStart(2, "0")}:00:00+08:00`,
      heat_index_max_c: 38 + h,
      temperature_max_c: 32,
      precipitation_max_mm: 0,
    }));
    mockApi({
      "/api/v1/transformers": [{ ...LIST[1], peak_ts: "2026-05-01T20:15:00+08:00" }, LIST[2]],
      "/api/v1/weather/outlook": outlook("fresh", hours),
    });
    renderAt("/engineer");
    expect(await screen.findByRole("img", { name: /Heat index by hour, 4 hours, 1 critical peaks marked/ })).toBeTruthy();
    expect(screen.getByText("Source: Open-Meteo")).toBeTruthy();
    expect(screen.getByText("Critical peak (1)")).toBeTruthy();
    expect(screen.queryByText("Rain, mm")).toBeNull();
  });

  it("shows an error with Try again when the outlook fails", async () => {
    mockApi({ "/api/v1/transformers": LIST });
    renderAt("/engineer");
    const strip = (await screen.findByRole("heading", { name: "Heat index, next 48 h" })).closest("section") as HTMLElement;
    expect(await within(strip).findByText("Could not load this view")).toBeTruthy();
  });
});

describe("ID search", () => {
  it("accepts T-106, t106, 106 and spaces", () => {
    for (const typed of ["T-106", "t106", "106", " t 106 ", "T 106"]) {
      expect(normalizeId(typed)).toBe("106");
      expect(matchesId("T-106", typed)).toBe(true);
    }
    expect(matchesId("T-106", "107")).toBe(false);
    expect(matchesId("T-106", "")).toBe(true);
  });
});

describe("transformer card", () => {
  it("says No data instead of a broken peak when there is no load", async () => {
    mockApi({
      "/api/v1/transformers/T-9": card("T-9", "Watch", 0.9, { load: [] }),
    });
    renderAt("/engineer/transformers/T-9");
    expect(await screen.findByText(/No forecast for the next 24 h/)).toBeTruthy();
    expect(screen.getAllByText("No data")).toHaveLength(2);
  });

  it("shows the reasons and the load chart, and remembers when it is folded", async () => {
    window.localStorage.removeItem("silip.card.loadHistoryOpen");
    mockApi({ "/api/v1/transformers/T-9": card("T-9", "Watch", 1.1) });
    renderAt("/engineer/transformers/T-9");
    expect(await screen.findByText("Why Watch")).toBeTruthy();
    expect(screen.getByText("Peak 110% of rating in the next 24 h, 80% in the last 48 h")).toBeTruthy();
    expect(screen.getByText("Simulated data")).toBeTruthy();
    expect(document.title).toBe("T-9 · Dashboard · SILIP");
    expect(screen.getByRole("img", { name: /Load as percent of rating/ })).toBeTruthy();
    expect(screen.getByText("Now")).toBeTruthy();
    expect(screen.getByText("100% = 90% of the 50 kVA nameplate (45 kVA)")).toBeTruthy();
    expect(screen.getByText("No heat-index forecast for this transformer yet.")).toBeTruthy();

    await userEvent.click(screen.getByRole("button", { name: /Load and heat index/ }));
    expect(screen.queryByRole("img", { name: /Load as percent of rating/ })).toBeNull();
    expect(window.localStorage.getItem("silip.card.loadHistoryOpen")).toBe("false");
    window.localStorage.removeItem("silip.card.loadHistoryOpen");
  });

  it("shows drivers as sentences with contribution bars when the model gave them", async () => {
    mockApi({
      "/api/v1/transformers/T-9": card("T-9", "Critical", 1.6, {
        drivers: [
          { feature: "heat_index", label: "Heat index 41 °C at the peak", value: 41, unit: "°C", contribution: 0.6, source: "Open-Meteo" },
          { feature: "coverage_pct", label: "40% of homes metered", value: 40, unit: "%", contribution: -0.2, source: "Clamps" },
        ],
      }),
    });
    renderAt("/engineer/transformers/T-9");
    expect(await screen.findByText("Heat index 41 °C at the peak")).toBeTruthy();
    expect(screen.getByText("Raises risk (+0.60)")).toBeTruthy();
    expect(screen.getByText("Lowers risk (−0.20)")).toBeTruthy();
    expect(screen.getByText("Bars: how much each reason moved the model score.")).toBeTruthy();
  });

  it("shows drivers as sentences only when the rules scorer gave no contributions", async () => {
    mockApi({
      "/api/v1/transformers/T-9": card("T-9", "Critical", 1.6, {
        drivers: [
          { feature: "peak_load_pct", label: "Peak forecast 160% of rating at 20:30", value: 160, unit: "% of rating", contribution: null, source: "Forecast" },
        ],
      }),
    });
    renderAt("/engineer/transformers/T-9");
    expect(await screen.findByText("Peak forecast 160% of rating at 20:30")).toBeTruthy();
    expect(screen.getByText("Source: Forecast.")).toBeTruthy();
    expect(screen.queryByText(/Raises risk/)).toBeNull();
    expect(screen.queryByText(/^Bars:/)).toBeNull();
  });

  it("offers one primary action, a copyable work order for Inspect before peak, and never Rebalance", async () => {
    mockApi({
      "/api/v1/transformers/T-9": card("T-9", "Critical", 1.6, { action: "Inspect before peak" }),
    });
    renderAt("/engineer/transformers/T-9");
    expect(await screen.findByRole("heading", { name: "Inspect before peak" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Copy work order summary" }).getAttribute("data-variant")).toBe("default");
    expect(document.querySelectorAll('main button[data-variant="default"], main a[data-variant="default"]')).toHaveLength(1);
    expect(screen.getByText("No per-phase data, so rebalancing can't be assessed.")).toBeTruthy();
    expect(screen.queryByText(/^Rebalance/)).toBeNull();
  });

  it("shows EV exposure with the adoption scenario labeled, or says adoption stats are not loaded", async () => {
    const station = { station_id: "s1", name: "Mall charger", lat: 14.58, lon: 121.0, barangay: null, city: "Pasig" };
    mockApi({
      "/api/v1/transformers/T-9": card("T-9", "Watch", 0.9, {
        ev_evening_step_kw: 3.25,
        ev: {
          stations_within: 1,
          nearest_station_m: 420.4,
          radius_m: 1000,
          stations: [station],
          adoption_scenario: {
            label: "Scenario, not a forecast",
            period: "2026-05",
            geography: "Philippines",
            metric: "ev_sales",
            vehicle_class: "bev",
            value: 1843,
            unit: "units",
            source_url: "https://example.org/report",
          },
        },
      }),
      "/api/v1/transformers/T-8": card("T-8", "Watch", 0.9),
    });
    const first = renderAt("/engineer/transformers/T-9");
    expect(await screen.findByText(/1 public charger within 1 km\. Nearest is 420 m away\./)).toBeTruthy();
    expect(screen.getByText("Scenario, not a forecast")).toBeTruthy();
    expect(screen.getByText(/Evening load step \+3\.3 kW/)).toBeTruthy();
    first.unmount();
    renderAt("/engineer/transformers/T-8");
    expect(await screen.findByText("Adoption stats not loaded.")).toBeTruthy();
    expect(screen.getByText(/No public chargers within 1 km\./)).toBeTruthy();
  });

  it("shows clamp health: clamps to target, online of installed and homes reporting", async () => {
    mockApi({
      "/api/v1/transformers/T-9": card("T-9", "Watch", 0.9, {
        action: "Add clamps",
        clamps_to_target: 6,
        clamp_health: { homes: 34, clamps_installed: 15, clamps_online: 12, homes_reporting: 12, reporting_pct: 12 / 34 },
      }),
    });
    renderAt("/engineer/transformers/T-9");
    expect(await screen.findByText("6 more clamps for target.")).toBeTruthy();
    expect(screen.getByText("12 of 15 installed")).toBeTruthy();
    expect(screen.getByText("12 of 34 (35%)")).toBeTruthy();
    expect(screen.getByRole("button", { name: "See clamp health" })).toBeTruthy();
  });

  it("shows an error with Try again when the card fails to load", async () => {
    mockApi({});
    renderAt("/engineer/transformers/T-404");
    expect(await screen.findByText("Could not load this view")).toBeTruthy();
  });

  it("offers Previous and Next in the list's order and filter", async () => {
    mockApi({
      "/api/v1/transformers": LIST,
      "/api/v1/transformers/T-3": card("T-3", "Watch", 0.95),
    });
    renderAt("/engineer/transformers/T-3");
    expect(await screen.findByText("2 of 3")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Previous: T-2" }).getAttribute("href")).toBe("/engineer/transformers/T-2");
    expect(screen.getByRole("link", { name: "Next: T-1" })).toBeTruthy();
    expect(
      within(screen.getByRole("navigation", { name: "Breadcrumb" }))
        .getByRole("link", { name: "Dashboard" })
        .getAttribute("href"),
    ).toBe("/engineer");
  });
});

describe("clamps", () => {
  it("judges a clamp's last report on the data's clock", () => {
    const asOf = "2026-04-30T23:44:59+08:00";
    expect(reportAge("2026-04-30T23:32:59+08:00", asOf)).toBe("Last report 12 min before data time");
    expect(reportAge("2026-04-30T20:44:59+08:00", asOf)).toBe("Last report 3 h before data time");
    expect(reportAge(null, asOf)).toBe("No report yet");
  });
});

describe("account", () => {
  it("confirms sign-out: Cancel keeps the session, Sign out ends it", async () => {
    mockApi({});
    renderAt("/");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Account: dev" }));
    await user.click(await screen.findByRole("menuitem", { name: "Sign out" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Sign out?" });
    expect(within(dialog).getByText("You will need your invitation account to sign in again.")).toBeTruthy();
    await waitFor(() => expect(document.activeElement?.textContent).toBe("Cancel"));
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(screen.getByRole("button", { name: "Account: dev" })).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "Account: dev" }));
    await user.click(await screen.findByRole("menuitem", { name: "Sign out" }));
    const again = await screen.findByRole("alertdialog", { name: "Sign out?" });
    await user.click(within(again).getByRole("button", { name: "Sign out" }));
    expect(await within(screen.getAllByRole("banner")[0]).findByRole("button", { name: "Sign in" })).toBeTruthy();
  });

  it("comes back to the protected page after the sign-in redirect", async () => {
    mockApi({ "/api/v1/transformers": LIST });
    let signedIn = false;
    const backend: AuthBackend = {
      load: async () => (signedIn ? devUser : null),
      signIn: async () => null, // a real redirect leaves the page
      completeSignIn: async () => {
        signedIn = true;
        return devUser;
      },
      signOut: async () => {},
    };
    const first = renderAt("/engineer", backend);
    await userEvent.click(await within(screen.getAllByRole("banner")[0]).findByRole("button", { name: "Sign in" }));
    expect(window.sessionStorage.getItem("silip.returnTo")).toBe("/engineer");
    expect(takeReturnPath()).toBe("/engineer");
    window.sessionStorage.setItem("silip.returnTo", "/engineer");
    first.unmount();

    renderAt("/auth/callback?code=abc", backend);
    expect(await screen.findByText("T-2")).toBeTruthy();
    expect(window.location.pathname).toBe("/engineer");
  });

  it("shows Try again and Back to home when the sign-in callback fails", async () => {
    const backend: AuthBackend = {
      ...createDevBackend(),
      completeSignIn: async () => {
        throw new Error("No matching state");
      },
    };
    vi.spyOn(console, "warn").mockImplementation(() => {});
    renderAt("/auth/callback?code=abc", backend);
    expect(await screen.findByText("Sign-in did not finish")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Try again" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Back to home" })).toBeTruthy();
  });
});

describe("navigation", () => {
  const signedOut: AuthBackend = { ...createDevBackend(), load: async () => null };

  it("shows visitors Home and How it works, with no engineer tabs", async () => {
    mockApi({});
    renderAt("/", signedOut);
    const nav = screen.getByRole("navigation", { name: "Main" });
    await within(nav).findByRole("link", { name: "Home" });
    const names = within(nav)
      .getAllByRole("link")
      .map((link) => link.getAttribute("aria-label") ?? link.textContent);
    expect(names).toEqual(["Home", "How it works"]);
    expect(within(nav).getByRole("link", { name: "Home" }).getAttribute("aria-current")).toBe("page");
  });

  it("shows engineers the dashboard and devices, with no Outages or My usage", async () => {
    mockApi({});
    renderAt("/");
    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(await within(nav).findByRole("link", { name: "Dashboard" })).toBeTruthy();
    expect(within(nav).getByRole("link", { name: "Devices" })).toBeTruthy();
    expect(within(nav).queryByRole("link", { name: "Outages" })).toBeNull();
    expect(within(nav).queryByRole("link", { name: /usage/i })).toBeNull();
  });

  it("lets a visitor cycle the theme from the header", async () => {
    mockApi({});
    window.localStorage.removeItem("silip.theme");
    renderAt("/sources", signedOut);
    const header = screen.getAllByRole("banner")[0];
    const user = userEvent.setup();
    await user.click(await within(header).findByRole("button", { name: "Theme: system" }));
    expect(document.documentElement.dataset.theme).toBe("light");
    await user.click(within(header).getByRole("button", { name: "Theme: light" }));
    expect(document.documentElement.dataset.theme).toBe("dark");
    await user.click(within(header).getByRole("button", { name: "Theme: dark" }));
    expect(document.documentElement.dataset.theme).toBeUndefined();
  });
});

describe("footer", () => {
  it("renders the about line, the sources link, How it works, Sign in and the simulated note on the landing page", async () => {
    mockApi({});
    renderAt("/", { ...createDevBackend(), load: async () => null });
    const footer = screen.getByRole("contentinfo");
    expect(within(footer).getByText("Built by Alventur Solutions for the Meralco Idol Hackathon 2026.")).toBeTruthy();
    expect(within(footer).getByRole("link", { name: "Data sources" }).getAttribute("href")).toBe("/sources");
    expect(within(footer).getByRole("link", { name: "How it works" })).toBeTruthy();
    expect(await within(footer).findByText("Items marked Simulated data use simulated readings.")).toBeTruthy();
    expect(await within(footer).findByRole("button", { name: "Sign in" })).toBeTruthy();
    expect(within(footer).queryByRole("link", { name: "Outages" })).toBeNull();
    expect(within(footer).getByRole("button", { name: /^Theme: / })).toBeTruthy();
  });

  it("gives engineers Dashboard instead of Sign in, and hides the simulated note when the data is real", async () => {
    mockApi({ "/api/v1/transformers": LIST.map((t) => ({ ...t, is_simulated: false, risk: { ...t.risk, is_simulated: false } })) });
    renderAt("/engineer");
    await screen.findByText("T-2");
    const footer = screen.getByRole("contentinfo");
    expect(await within(footer).findByRole("link", { name: "Dashboard" })).toBeTruthy();
    expect(within(footer).queryByRole("button", { name: "Sign in" })).toBeNull();
    expect(within(footer).queryByText(/simulated/)).toBeNull();
  });
});

describe("not found page", () => {
  const as = (groups: "engineers"[]): AuthBackend => ({
    ...createDevBackend(),
    load: async () => ({ ...devUser, groups }),
  });
  const linksIn = (main: HTMLElement) =>
    within(main)
      .getAllByRole("link")
      .map((link) => [link.textContent, link.getAttribute("data-variant")]);

  it("offers Home to visitors as the one primary button", async () => {
    mockApi({});
    renderAt("/no-such-page", { ...createDevBackend(), load: async () => null });
    const main = screen.getByRole("main");
    expect(await within(main).findByText("This link may be old or mistyped.")).toBeTruthy();
    expect(linksIn(main)).toEqual([["Home", "default"]]);
    expect(document.title).toBe("Page not found · SILIP");
  });

  it("leads engineers to the dashboard", async () => {
    mockApi({});
    renderAt("/no-such-page", as(["engineers"]));
    const main = screen.getByRole("main");
    expect(await within(main).findByRole("link", { name: "Dashboard" })).toBeTruthy();
    expect(linksIn(main)).toEqual([
      ["Dashboard", "default"],
      ["Home", "outline"],
    ]);
  });

});

describe("data sources page", () => {
  it("lists the sources from the spec", () => {
    mockApi({});
    renderAt("/sources");
    expect(screen.getByRole("heading", { level: 1, name: "Data sources" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "powerphilippines.com/?p=23852 (opens in a new tab)" })).toBeTruthy();
    expect(screen.getByText("Daily Tribune, 23 Sep 2026")).toBeTruthy();
    expect(document.title).toBe("Data sources · SILIP");
  });
});

describe("return path", () => {
  it("never leaves the site", () => {
    for (const unsafe of ["//evil.example", "/\\evil.example", "https://evil.example", "/auth/callback"]) {
      window.sessionStorage.setItem("silip.returnTo", unsafe);
      expect(takeReturnPath()).toBe("/");
    }
  });
});

describe("live demo page", () => {
  const home = (label: string, watts: number) => ({
    label,
    watts,
    volts: 11.4,
    powered: true,
    updated_at: "2026-11-12T13:00:00Z",
  });
  const BENCH = {
    as_of: "2026-11-12T13:00:00Z",
    mode: "replay",
    is_simulated: true,
    sample_interval_s: 2,
    transformers: [
      {
        transformer_id: "BENCH-T1",
        rated_w: 4.6,
        total_w: 5.9,
        load_pct: 1.28,
        tier: "Critical",
        reasons: ["Load 128% of rating now", "House 3 added a large new load (likely EV)"],
        homes_reporting: 4,
        homes_on_record: 4,
        homes: [home("House 1", 1.1), home("House 3", 3.0)],
        powered: true,
      },
    ],
    fingerprints: [
      {
        home: "House 4",
        record_transformer: "BENCH-T1",
        voltage_transformer: "BENCH-T2",
        confidence: 0.87,
        mismatch: true,
        explanation: "Voltage dips with BENCH-T2, not BENCH-T1.",
      },
    ],
  };

  it("opens with no sign-in and labels simulated rows as Replay (simulated)", async () => {
    mockApi({ "/api/v1/bench": BENCH });
    renderAt("/demo", { ...createDevBackend(), load: async () => null });
    expect(await screen.findByText("Replay (simulated)")).toBeTruthy();
    expect(screen.getByText("House 3 added a large new load (likely EV)")).toBeTruthy();
    expect(screen.getByText(/House 4: records say T1, voltage says T2 \(confidence 87%\)/)).toBeTruthy();
    expect(screen.getByText(/built from 4 of 4 homes by SIN/)).toBeTruthy();
    expect(document.head.querySelector('meta[name="robots"]')?.getAttribute("content")).toBe("noindex");
  });
});
