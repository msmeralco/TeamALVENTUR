import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { createDevBackend } from "../shared/auth";

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

function mockApi(body: unknown, status = 200) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } })),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("public outage view", () => {
  it("shows the restoration range and the Simulated data label", async () => {
    mockApi([OUTAGE]);
    render(<App backend={createDevBackend()} />);
    expect(await screen.findByText("Cause: overload")).toBeTruthy();
    expect(screen.getByText(/1 h 30 min to 5 h 0 min/)).toBeTruthy();
    expect(screen.getByText("Simulated data")).toBeTruthy();
  });

  it("shows an error with a retry when the API fails", async () => {
    mockApi({ detail: "boom" }, 500);
    render(<App backend={createDevBackend()} />);
    expect(await screen.findByRole("alert", {}, { timeout: 3000 })).toBeTruthy();
  });
});
