"""Weather: Open-Meteo parsing, retries and budget with a fake transport; simulated forecasts;
refresh at most hourly with a fallback to the stored forecast. Never calls the real API."""

import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from silip.weather.adapters import HttpError, OpenMeteoClient, SimulatedWeather, parse_forecast
from silip.weather.domain import WEATHER_COLUMNS, Cell, WeatherFetchError
from silip.weather.service import cells_for, forecast_rows, outlook, refresh
from silip_ml.weather import cell_id, heat_index_c

BASE = "https://api.open-meteo.test/v1/forecast"
CELLS = [Cell("14.55_121.05", 14.55, 121.05), Cell("14.65_121.05", 14.65, 121.05)]
NOW = datetime(2026, 11, 13, 6, tzinfo=UTC)


def _location(lat: float, temps: list[float]) -> dict:
    return {
        "latitude": lat + 0.01,  # snapped to the provider's grid
        "longitude": 121.04,
        "utc_offset_seconds": 8 * 3600,
        "timezone": "Asia/Manila",
        "hourly": {
            "time": [f"2026-11-13T{hour:02d}:00" for hour in range(len(temps))],
            "temperature_2m": temps,
            "relative_humidity_2m": [70] * len(temps),
            "precipitation": [0.0] * len(temps),
        },
    }


BODY = json.dumps([_location(14.55, [30.0, 31.0]), _location(14.65, [32.0, 33.0])]).encode()


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class FakeTransport:
    """Replays `outcomes` (bytes or an exception); records each call's URL and timeouts."""

    def __init__(self, clock: FakeClock, *outcomes: bytes | Exception, cost_s: float = 0.0) -> None:
        self.clock = clock
        self.outcomes = list(outcomes)
        self.cost_s = cost_s
        self.calls: list[tuple[str, float, float]] = []

    def __call__(self, url: str, connect_timeout: float, read_timeout: float) -> bytes:
        self.calls.append((url, connect_timeout, read_timeout))
        self.clock.now += self.cost_s
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _client(
    *outcomes: bytes | Exception, cost_s: float = 0.0
) -> tuple[OpenMeteoClient, FakeTransport, FakeClock]:
    clock = FakeClock()
    transport = FakeTransport(clock, *outcomes, cost_s=cost_s)
    return OpenMeteoClient(BASE, transport, clock.sleep, clock), transport, clock


def test_one_request_for_all_cells_with_the_agreed_query() -> None:
    client, transport, _ = _client(BODY)

    client.fetch(CELLS)

    [(url, connect_timeout, read_timeout)] = transport.calls
    assert "latitude=14.5500,14.6500" in url and "longitude=121.0500,121.0500" in url
    assert "hourly=temperature_2m,relative_humidity_2m,precipitation" in url
    assert "forecast_days=3" in url and "timezone=Asia/Manila" in url
    assert (connect_timeout, read_timeout) == (5.0, 10.0)


def test_parses_several_locations_in_request_order() -> None:
    rows = parse_forecast(BODY, CELLS)

    assert rows["cell_id"].tolist() == ["14.55_121.05"] * 2 + ["14.65_121.05"] * 2
    assert rows["lat"].tolist() == [14.55, 14.55, 14.65, 14.65]  # the cell's point, not the grid's
    assert rows["temperature_c"].tolist() == [30.0, 31.0, 32.0, 33.0]
    assert rows["ts"].iloc[0] == pd.Timestamp("2026-11-12T16:00:00Z")  # 00:00 Manila


def test_parses_a_single_location_object() -> None:
    rows = parse_forecast(json.dumps(_location(14.55, [30.0])).encode(), CELLS[:1])

    assert len(rows) == 1


@pytest.mark.parametrize("body", [b"not json", b"[]", json.dumps([{"hourly": {}}] * 2).encode()])
def test_unreadable_body_is_a_fetch_error(body: bytes) -> None:
    with pytest.raises(WeatherFetchError):
        parse_forecast(body, CELLS)


def test_retries_twice_with_backoff_then_succeeds() -> None:
    client, transport, clock = _client(TimeoutError(), HttpError(503), BODY)

    rows = client.fetch(CELLS)

    assert len(rows) == 4
    assert len(transport.calls) == 3
    assert clock.sleeps == [1.0, 3.0]


def test_gives_up_after_two_retries() -> None:
    client, transport, _ = _client(OSError(), OSError(), OSError(), BODY)

    with pytest.raises(WeatherFetchError):
        client.fetch(CELLS)
    assert len(transport.calls) == 3


def test_client_error_is_not_retried() -> None:
    client, transport, _ = _client(HttpError(400), BODY)

    with pytest.raises(WeatherFetchError):
        client.fetch(CELLS)
    assert len(transport.calls) == 1


def test_overall_budget_caps_timeouts_and_retries() -> None:
    # Each attempt times out after 14 s; the 30 s budget leaves no room for a third attempt.
    client, transport, _ = _client(TimeoutError(), TimeoutError(), BODY, cost_s=14.0)

    with pytest.raises(WeatherFetchError):
        client.fetch(CELLS)
    assert len(transport.calls) == 2
    assert transport.calls[1][2] == pytest.approx(10.0)  # 30 - 14 - 1 = 15 s left, capped at 10


def test_forecast_rows_add_heat_index_and_issue_time() -> None:
    rows = forecast_rows(parse_forecast(BODY, CELLS), NOW)

    assert list(rows.columns) == WEATHER_COLUMNS
    assert rows["heat_index_c"].iloc[0] == pytest.approx(heat_index_c(30.0, 70.0))
    assert (rows["issued_at"] == NOW).all() and not rows["is_simulated"].any()


def test_cells_group_transformers_by_cell() -> None:
    transformers = pd.DataFrame({"lat": [14.551, 14.559, 14.651], "lon": [121.04, 121.04, 121.04]})

    cells = cells_for(transformers)

    assert [cell.cell_id for cell in cells] == sorted(
        {cell_id(14.551, 121.04), cell_id(14.651, 121.04)}
    )
    assert cells[0].lat == pytest.approx(14.555)


class MemoryStore:
    def __init__(self) -> None:
        self.rows = pd.DataFrame(columns=WEATHER_COLUMNS)

    def insert(self, rows: pd.DataFrame) -> int:
        self.rows = pd.concat([self.rows, rows], ignore_index=True) if len(self.rows) else rows
        return len(rows)

    def latest(self, as_of: datetime) -> pd.DataFrame:
        issued = self.rows.loc[self.rows["issued_at"] <= as_of, "issued_at"]
        return (
            self.rows.iloc[0:0]
            if issued.empty
            else self.rows[self.rows["issued_at"] == issued.max()]
        )


class FailingFetcher:
    calls = 0

    def fetch(self, cells: Sequence[Cell]) -> pd.DataFrame:
        self.calls += 1
        raise WeatherFetchError("down")


def test_refresh_fetches_stores_and_then_waits_an_hour() -> None:
    client, transport, _ = _client(BODY, BODY)
    store = MemoryStore()

    first = refresh(CELLS, NOW, client, store)
    again = refresh(CELLS, NOW + timedelta(minutes=30), client, store)

    assert first.status == "fresh" and first.issued_at == NOW and len(first.rows) == 4
    assert again.issued_at == NOW
    assert len(transport.calls) == 1


def test_refresh_failure_falls_back_to_stored_then_stale_then_missing() -> None:
    store = MemoryStore()
    store.insert(forecast_rows(parse_forecast(BODY, CELLS), NOW))
    fetcher = FailingFetcher()

    assert refresh(CELLS, NOW + timedelta(hours=2), fetcher, store).status == "fresh"
    assert refresh(CELLS, NOW + timedelta(hours=7), fetcher, store).status == "stale"
    missing = refresh(CELLS, NOW + timedelta(hours=25), fetcher, store)
    assert missing.status == "missing" and missing.rows.empty
    assert fetcher.calls == 3


def test_simulated_weather_without_file_is_missing(tmp_path: Path) -> None:
    assert outlook(SimulatedWeather(tmp_path), NOW).status == "missing"


def test_simulated_weather_takes_latest_issue_before_now(tmp_path: Path) -> None:
    pd.DataFrame(
        {
            "cell_id": ["c"] * 3,
            "ts": ["2026-11-13T12:00:00Z"] * 3,
            "issued_at": ["2026-11-12T00:00:00Z", "2026-11-13T00:00:00Z", "2026-11-14T00:00:00Z"],
            "heat_index_c": [38.0, 39.0, 40.0],
            "is_simulated": [True] * 3,
        }
    ).to_csv(tmp_path / "weather_forecast_hourly.csv", index=False)

    result = outlook(SimulatedWeather(tmp_path), NOW)

    assert result.status == "fresh" and result.is_simulated
    assert result.rows["heat_index_c"].tolist() == [39.0]
    assert result.rows["kind"].tolist() == ["forecast"]
