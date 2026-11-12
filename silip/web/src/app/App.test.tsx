import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { createDevBackend, devUser, takeReturnPath, type AuthBackend } from "../shared/auth";
import { matchesId, normalizeId, reportAge } from "../shared/risk";
import { dailyKwh } from "../features/household/UsagePage";

// MapLibre needs WebGL, which jsdom lacks; the list beside the map carries the same data.
vi.mock("../features/risk-map/TransformerMap", () => ({ TransformerMap: () => null }));
vi.mock("../features/devices/InstallationMap", () => ({ InstallationMap: () => null }));

const OUTAGE = {
  outage_id: "O-0001",
  status: "open",
  cause: "overload",
  started_at: "2026-04-30T20:15:00+08:00",
  area_lat: 14.581,
  area_lon: 121.002,
  eta_p10_min: 90,
  eta_p50_min: 180,
  eta_p90_min: 300,
  is_simulated: true,
};

function risk(id: string, tier: "OK" | "Watch" | "Critical", peak: number) {
  return {
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

const LIST = [risk("T-1", "OK", 0.5), risk("T-2", "Critical", 1.2), risk("T-3", "Watch", 0.95)];
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

describe("public outage view", () => {
  it("leads with the expected time back, shows the window once, the cause and the Simulated data label", async () => {
    mockApi({ "/api/v1/outages": [OUTAGE] });
    renderAt("/outages");
    expect(await screen.findByText("overload")).toBeTruthy();
    expect(screen.getByText(/^Expected back around /)).toBeTruthy();
    expect(screen.getAllByText(/^Window /)).toHaveLength(1);
    expect(screen.getByText("Power out")).toBeTruthy();
    expect(screen.queryByText(/1 h 30 min/)).toBeNull();
    expect(screen.getByText("Simulated data")).toBeTruthy();
    expect(screen.getAllByText(/^Updated /).length).toBeGreaterThan(0);
    expect(document.title).toBe("Outages · SILIP");
  });

  it("hides the area search until the API sends area names", async () => {
    mockApi({ "/api/v1/outages": [OUTAGE] });
    renderAt("/outages");
    await screen.findByText("overload");
    expect(screen.queryByRole("searchbox", { name: "Search by area" })).toBeNull();
    expect(screen.getByRole("button", { name: "Near me" })).toBeTruthy();
  });

  it("says calmly when nothing is out and keeps the advice to report to Meralco", async () => {
    mockApi({ "/api/v1/outages": [] });
    renderAt("/outages");
    expect(await screen.findByText("No open outages in this area.")).toBeTruthy();
    expect(screen.getByText("If your power is out, report it to Meralco.")).toBeTruthy();
  });

  it("shows an error with a retry when the API fails", async () => {
    mockApi({ "/api/v1/outages": { detail: "boom" } }, 500);
    renderAt("/outages");
    const alert = await screen.findByRole("alert", {}, { timeout: 3000 });
    expect(within(alert).getByRole("button", { name: "Try again" })).toBeTruthy();
  });
});

describe("landing page", () => {
  it("opens on the outage check, then How it works and the labeled engineer example", async () => {
    mockApi({ "/api/v1/outages": [OUTAGE] });
    renderAt("/");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toMatch(/^SILIP estimates/);
    expect(screen.getByRole("button", { name: "Near me" })).toBeTruthy();
    expect(await screen.findByText("overload")).toBeTruthy();
    expect(document.getElementById("how-it-works")?.querySelector("h2")?.textContent).toBe("How it works");
    expect(screen.getByText("Example from simulated data")).toBeTruthy();
    expect(document.title).toBe("SILIP");
  });

  it("sends old outage links with a query on / to /outages, keeping the query", async () => {
    mockApi({ "/api/v1/outages": [OUTAGE] });
    renderAt("/?area=pasig");
    expect(await screen.findByRole("heading", { level: 1, name: "Power outages" })).toBeTruthy();
    expect(window.location.pathname).toBe("/outages");
    expect(window.location.search).toBe("?area=pasig");
  });
});

describe("engineer risk map", () => {
  it("groups Critical as Needs action first, then Watch, with OK folded", async () => {
    mockApi({ "/api/v1/transformers": LIST });
    renderAt("/engineer");
    await screen.findByText("T-2");
    const sections = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent ?? "");
    expect(sections[0]).toMatch(/^Needs action/);
    expect(sections[1]).toMatch(/^Watch/);
    expect(sections[2]).toMatch(/^OK/);
    expect(screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual(["T-2", "T-3"]);
    expect(screen.getByText("Simulated data")).toBeTruthy();
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
      "/api/v1/transformers/T-9": { ...risk("T-9", "Watch", 0.9), as_of: "2026-04-30T20:15:00+08:00", load: [] },
    });
    renderAt("/engineer/transformers/T-9");
    expect(await screen.findByText(/No forecast for the next 24 h/)).toBeTruthy();
    expect(screen.getAllByText("No data")).toHaveLength(2);
  });

  it("puts the reasons first and keeps load history collapsed until asked", async () => {
    mockApi({
      "/api/v1/transformers/T-9": { ...risk("T-9", "Watch", 1.1), as_of: "2026-04-30T20:15:00+08:00", load: LOAD },
    });
    renderAt("/engineer/transformers/T-9");
    expect(await screen.findByText("Why Watch")).toBeTruthy();
    expect(screen.getByText("Peak 110% of rating in the next 24 h, 80% in the last 48 h")).toBeTruthy();
    expect(screen.queryByRole("img", { name: /Load as percent of rating/ })).toBeNull();
    expect(screen.getByText("Simulated data")).toBeTruthy();
    expect(document.title).toBe("T-9 · Risk map · SILIP");

    await userEvent.click(screen.getByRole("button", { name: /Load history/ }));
    expect(screen.getByRole("img", { name: /Load as percent of rating/ })).toBeTruthy();
    expect(screen.getByText("Now")).toBeTruthy();
    expect(screen.getByText("100% = 90% of the 50 kVA nameplate (45 kVA)")).toBeTruthy();
  });

  it("offers Previous and Next in the list's order and filter", async () => {
    mockApi({
      "/api/v1/transformers": LIST,
      "/api/v1/transformers/T-3": { ...risk("T-3", "Watch", 0.95), as_of: "2026-04-30T20:15:00+08:00", load: LOAD },
    });
    renderAt("/engineer/transformers/T-3");
    expect(await screen.findByText("2 of 3")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Previous: T-2" }).getAttribute("href")).toBe("/engineer/transformers/T-2");
    expect(screen.getByRole("link", { name: "Next: T-1" })).toBeTruthy();
    expect(
      within(screen.getByRole("navigation", { name: "Breadcrumb" }))
        .getByRole("link", { name: "Risk map" })
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

  const clamp = (id: string, transformer: string, status: "online" | "offline") => ({
    clamp_id: id,
    transformer_id: transformer,
    lat: 14.58,
    lon: 121.0,
    ct_model: "SCT-013-000",
    installed_at: "2026-01-29T07:43:00+08:00",
    last_seen_at: "2026-04-30T23:33:44+08:00",
    status,
    is_simulated: true,
  });

  it("says None installed when a transformer has no clamps", async () => {
    mockApi({
      "/api/v1/transformers/T-9": { ...risk("T-9", "Watch", 0.9), as_of: "2026-04-30T20:15:00+08:00", load: LOAD },
      "/api/v1/clamps": { as_of: null, offline_after_min: 60, is_simulated: true, clamps: [] },
    });
    renderAt("/engineer/transformers/T-9");
    expect(await screen.findByText("None installed")).toBeTruthy();
  });

  it("says clamp status is unavailable, with Retry, when clamps fail to load", async () => {
    mockApi({
      "/api/v1/transformers/T-9": { ...risk("T-9", "Watch", 0.9), as_of: "2026-04-30T20:15:00+08:00", load: LOAD },
    });
    renderAt("/engineer/transformers/T-9");
    expect(await screen.findByText("Clamp status unavailable")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Retry" })).toBeTruthy();
  });

  it("shows how many of a transformer's clamps are online on its card", async () => {
    mockApi({
      "/api/v1/transformers/T-9": { ...risk("T-9", "Watch", 0.9), as_of: "2026-04-30T20:15:00+08:00", load: LOAD },
      "/api/v1/clamps": {
        as_of: "2026-04-30T23:44:59+08:00",
        offline_after_min: 60,
        is_simulated: true,
        clamps: [clamp("n-1", "T-9", "online"), clamp("n-2", "T-9", "offline"), clamp("n-3", "T-8", "online")],
      },
    });
    renderAt("/engineer/transformers/T-9");
    expect(await screen.findByText("Clamps online")).toBeTruthy();
    expect(screen.getByText("1 of 2")).toBeTruthy();
  });
});

describe("account", () => {
  it("confirms sign-out: Cancel keeps the session, Sign out ends it", async () => {
    mockApi({ "/api/v1/outages": [OUTAGE] });
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

  it("shows Try again and Back to outages when the sign-in callback fails", async () => {
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
    expect(screen.getByRole("link", { name: "Back to outages" })).toBeTruthy();
  });
});

describe("navigation", () => {
  const signedOut: AuthBackend = { ...createDevBackend(), load: async () => null };

  it("shows visitors Home, Outages and How it works, with no engineer or household tabs", async () => {
    mockApi({ "/api/v1/outages": [OUTAGE] });
    renderAt("/outages", signedOut);
    const nav = screen.getByRole("navigation", { name: "Main" });
    await within(nav).findByRole("link", { name: "Home" });
    const names = within(nav)
      .getAllByRole("link")
      .map((link) => link.getAttribute("aria-label") ?? link.textContent);
    expect(names).toEqual(["Home", "Outages", "How it works"]);
    expect(within(nav).getByRole("link", { name: "Outages" }).getAttribute("aria-current")).toBe("page");
    expect(within(nav).getByRole("link", { name: "Home" }).getAttribute("aria-current")).toBeNull();
  });

  it("shows signed-in users their own views plus Outages", async () => {
    mockApi({ "/api/v1/outages": [OUTAGE] });
    renderAt("/outages");
    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(await within(nav).findByRole("link", { name: "Risk map" })).toBeTruthy();
    expect(within(nav).getByRole("link", { name: "Outages" })).toBeTruthy();
    expect(within(nav).queryByRole("link", { name: "Home" })).toBeNull();
  });

  it("lets a visitor cycle the theme from the header", async () => {
    mockApi({ "/api/v1/outages": [OUTAGE] });
    window.localStorage.removeItem("silip.theme");
    renderAt("/outages", signedOut);
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
  it("renders the about line, the sources link and the simulated note once data is simulated", async () => {
    mockApi({ "/api/v1/outages": [OUTAGE] });
    renderAt("/outages", { ...createDevBackend(), load: async () => null });
    const footer = screen.getByRole("contentinfo");
    expect(within(footer).getByText("Built by Alventur Solutions for the Meralco Idol Hackathon 2026.")).toBeTruthy();
    expect(within(footer).getByRole("link", { name: "Data sources" }).getAttribute("href")).toBe("/sources");
    expect(await within(footer).findByText("Readings shown are simulated unless marked otherwise.")).toBeTruthy();
    expect(await within(footer).findByRole("button", { name: "Sign in" })).toBeTruthy();
    expect(within(footer).getByRole("button", { name: /^Theme: / })).toBeTruthy();
  });

  it("hides the simulated note and Sign in when nothing simulated loaded and the viewer is signed in", async () => {
    mockApi({});
    renderAt("/sources");
    const footer = screen.getByRole("contentinfo");
    await waitFor(() => expect(within(footer).queryByRole("button", { name: "Sign in" })).toBeNull());
    expect(within(footer).queryByText(/simulated/)).toBeNull();
  });
});

describe("not found page", () => {
  const as = (groups: ("engineers" | "households")[]): AuthBackend => ({
    ...createDevBackend(),
    load: async () => ({ ...devUser, groups }),
  });
  const linksIn = (main: HTMLElement) =>
    within(main)
      .getAllByRole("link")
      .map((link) => [link.textContent, link.getAttribute("data-variant")]);

  it("offers Home and Outages to visitors, with Home as the one primary button", async () => {
    mockApi({});
    renderAt("/no-such-page", { ...createDevBackend(), load: async () => null });
    const main = screen.getByRole("main");
    expect(await within(main).findByText("This link may be old or mistyped.")).toBeTruthy();
    expect(linksIn(main)).toEqual([
      ["Home", "default"],
      ["Outages", "outline"],
    ]);
    expect(document.title).toBe("Page not found · SILIP");
  });

  it("leads engineers to the risk map", async () => {
    mockApi({});
    renderAt("/no-such-page", as(["engineers"]));
    const main = screen.getByRole("main");
    expect(await within(main).findByRole("link", { name: "Risk map" })).toBeTruthy();
    expect(linksIn(main)).toEqual([
      ["Risk map", "default"],
      ["Home", "outline"],
      ["Outages", "outline"],
    ]);
  });

  it("leads households to their usage", async () => {
    mockApi({});
    renderAt("/no-such-page", as(["households"]));
    const main = screen.getByRole("main");
    expect(await within(main).findByRole("link", { name: "My usage" })).toBeTruthy();
    expect(linksIn(main)).toEqual([
      ["My usage", "default"],
      ["Home", "outline"],
      ["Outages", "outline"],
    ]);
  });
});

describe("data sources page", () => {
  it("lists the sources from the spec", () => {
    mockApi({});
    renderAt("/sources");
    expect(screen.getByRole("heading", { level: 1, name: "Data sources" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "powerphilippines.com/?p=23852" })).toBeTruthy();
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

describe("household usage", () => {
  it("labels simulated data and marks partial days", async () => {
    const points = [
      { ts: "2026-11-10T10:00:00", kw: 2 },
      { ts: "2026-11-10T10:15:00", kw: 2 },
    ];
    mockApi({ "/api/v1/me/usage": { total_kwh: 1, points, is_simulated: true } });
    renderAt("/me/usage");
    expect(await screen.findByText("partial day")).toBeTruthy();
    expect(screen.getByText("Simulated data")).toBeTruthy();
  });
});

describe("dailyKwh", () => {
  it("sums 15-minute kW readings into kWh per day, oldest first", () => {
    const days = dailyKwh([
      { ts: "2026-11-11T10:00:00", kw: 2 },
      { ts: "2026-11-10T10:00:00", kw: 4 },
      { ts: "2026-11-11T10:15:00", kw: 2 },
    ]);
    expect(days.map((d) => d.kwh)).toEqual([1, 1]);
    expect(days[0].day.getDate()).toBe(10);
    expect(days.every((d) => !d.complete)).toBe(true);
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
  });
});
