"""Dashboard routes on simulated data: auth, shapes, labels, and what they never contain."""

import json
import re

import pandas as pd
import pytest

from silip.app import app
from silip.dashboard.domain import ACTIONS, TARGET_COVERAGE, TIERS
from silip.shared.deps import get_data_source
from silip.shared.readings.adapters import SimulatedSource
from silip_ml.ev import EV_STATION_RADIUS_M
from tests.api.helpers import auth

ENGINEER = auth("engineer-token")
ROUTES = [
    "/api/v1/dashboard/summary",
    "/api/v1/weather/outlook",
    "/api/v1/ev/chargers",
    "/api/v1/ev/adoption",
    "/api/v1/clamps/coverage",
    "/api/v1/transformers",
]


class DayEarlier(SimulatedSource):
    """The simulator issues forecasts only inside its own window, so the last day has no hours
    ahead. Ending the load a day early leaves a day of forecast after the latest interval."""

    def load(self, since=None):
        load = super().load(since)
        return load[load["ts"] <= self._end]

    def latest_load_ts(self):
        return self._end

    @property
    def _end(self) -> pd.Timestamp:
        latest = super().latest_load_ts()
        assert latest is not None
        return latest - pd.Timedelta(days=1)


@pytest.fixture
def ahead(sim_dir):
    """The app on DayEarlier for one test."""
    saved = dict(app.dependency_overrides)
    source = DayEarlier(sim_dir)
    app.dependency_overrides[get_data_source] = lambda: source
    yield source
    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved)


@pytest.mark.parametrize("route", ROUTES)
def test_dashboard_routes_are_engineer_only(client, route):
    assert client.get(route).status_code == 401
    assert client.get(route, headers=auth("household-token")).status_code == 403
    assert client.get(route, headers=ENGINEER).status_code == 200


def test_household_routes_are_gone(client):
    for route in ("/api/v1/me/usage", "/api/v1/me/device"):
        assert client.get(route, headers=auth("household-token")).status_code == 404


def test_summary_counts_tiers_and_actions_and_labels_simulated(client, dataset, ahead):
    body = client.get("/api/v1/dashboard/summary", headers=ENGINEER).json()
    count = len(dataset.transformers)
    assert list(body["tiers"]) == list(TIERS) and sum(body["tiers"].values()) == count
    assert list(body["actions"]) == list(ACTIONS) and sum(body["actions"].values()) == count
    assert body["weather"]["source"] == "Simulated"
    assert body["weather"]["status"] in {"fresh", "stale"}
    assert body["weather"]["heat_index_max_c"] is not None
    assert body["clamps"]["online"] <= body["clamps"]["installed"]
    assert body["model"]["risk_scorer"] == "rules" and body["model"]["kept"] is None
    assert body["is_simulated"] is True


def test_summary_bbox_narrows_and_rejects_bad_input(client):
    empty = client.get("/api/v1/dashboard/summary?bbox=0,0,1,1", headers=ENGINEER).json()
    assert sum(empty["tiers"].values()) == 0
    bad = client.get("/api/v1/dashboard/summary?bbox=1,2", headers=ENGINEER)
    assert bad.status_code == 422


def test_transformer_rows_carry_the_queue_fields(client, dataset, ahead):
    body = client.get("/api/v1/transformers", headers=ENGINEER).json()
    homes = dict(
        zip(dataset.transformers["transformer_id"], dataset.transformers["homes"], strict=True)
    )
    for row in body:
        assert row["action"] in ACTIONS
        assert row["peak_ts"] is not None
        assert row["top_reason"] == row["risk"]["reasons"][0]
        assert row["heat_index_max_c"] is not None
        health = row["clamp_health"]
        assert health["homes"] == homes[row["transformer_id"]]
        assert health["homes_reporting"] == health["clamps_online"] <= health["clamps_installed"]
        assert isinstance(row["open_outage"], bool)
    by_id = {row["transformer_id"]: row for row in body}
    assert by_id["T-100"]["ev_stations_within"] == 1  # the fixture station 40 m away
    assert by_id["T-101"]["ev_stations_within"] == 0


def test_card_has_drivers_weather_ev_and_clamp_target(client, ahead):
    card = client.get("/api/v1/transformers/T-100", headers=ENGINEER).json()
    assert 1 <= len(card["drivers"]) <= 3
    assert {"feature", "label", "value", "unit", "contribution", "source"} <= set(
        card["drivers"][0]
    )
    assert card["drivers"][0]["label"] == card["risk"]["reasons"][0]
    hours = [pd.Timestamp(point["ts"]) for point in card["weather"]]
    assert 0 < len(hours) <= 48 and hours == sorted(hours)
    ev = card["ev"]
    assert ev["radius_m"] == EV_STATION_RADIUS_M and ev["stations_within"] == 1
    assert ev["stations"][0]["name"] == "Test Hub Near T-100"
    assert ev["nearest_station_m"] < 100
    assert ev["adoption_scenario"] is None  # no adoption file delivered
    health = card["clamp_health"]
    expected = max(
        0, -(-int(TARGET_COVERAGE * 100) * health["homes"] // 100) - health["clamps_online"]
    )
    assert card["clamps_to_target"] == expected


def test_weather_outlook_is_48_hours_labeled_simulated(client, ahead):
    body = client.get("/api/v1/weather/outlook", headers=ENGINEER).json()
    assert body["source"] == "Simulated" and body["is_simulated"] is True
    assert 0 < len(body["hours"]) <= 48
    assert body["cells"] and all(cell["heat_index_max_c"] is not None for cell in body["cells"])
    empty = client.get("/api/v1/weather/outlook?bbox=0,0,1,1", headers=ENGINEER).json()
    assert empty["hours"] == [] and empty["cells"] == []


def test_ev_chargers_filter_by_bbox_and_adoption_is_not_loaded(client):
    every = client.get("/api/v1/ev/chargers", headers=ENGINEER).json()
    assert len(every["stations"]) == 3 and every["radius_m"] == EV_STATION_RADIUS_M
    luzon = client.get("/api/v1/ev/chargers?bbox=120,14,122,15", headers=ENGINEER).json()
    assert {s["name"] for s in luzon["stations"]} == {"Test Hub Near T-100", "Test Hub Near T-103"}
    adoption = client.get("/api/v1/ev/adoption", headers=ENGINEER).json()
    assert adoption == {
        "status": "not_loaded",
        "series": [],
        "source_url": None,
        "is_simulated": False,
    }


def test_clamp_coverage_is_counts_per_transformer(client, dataset):
    body = client.get("/api/v1/clamps/coverage", headers=ENGINEER).json()
    assert len(body["transformers"]) == len(dataset.transformers)
    assert body["target_coverage"] == TARGET_COVERAGE
    rows = body["transformers"]
    assert [r["clamp_health"]["reporting_pct"] for r in rows] == sorted(
        r["clamp_health"]["reporting_pct"] for r in rows
    )
    assert body["clamps"]["installed"] == sum(r["clamp_health"]["clamps_installed"] for r in rows)
    assert body["is_simulated"] is True


SIN_HASH = re.compile(r"\b[0-9a-f]{64}\b")
CLAMP_ID = re.compile(r"silip-node-\d+")


def test_dashboard_payloads_never_carry_household_identity_or_home_location(client, dataset):
    homes = pd.read_csv("tests/fixtures/sim/sin_map.csv").dropna(subset=["lat", "lon"])
    home_points = {
        (round(lat, 5), round(lon, 5)) for lat, lon in zip(homes["lat"], homes["lon"], strict=True)
    }
    for route in [*ROUTES, "/api/v1/transformers/T-100", "/api/v1/transformers/T-103"]:
        body = client.get(route, headers=ENGINEER).json()
        text = json.dumps(body)
        assert "sin_hash" not in text and "clamp_id" not in text, route
        assert not SIN_HASH.search(text) and not CLAMP_ID.search(text), route
        for lat, lon in _points(body):
            assert (round(lat, 5), round(lon, 5)) not in home_points, route


def _points(value):
    """Every (lat, lon) pair anywhere in a JSON body."""
    if isinstance(value, dict):
        if "lat" in value and "lon" in value:
            yield value["lat"], value["lon"]
        for child in value.values():
            yield from _points(child)
    elif isinstance(value, list):
        for child in value:
            yield from _points(child)
