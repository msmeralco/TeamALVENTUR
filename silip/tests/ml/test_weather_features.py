"""Weather and EV features: no look-ahead, same definitions as the notebooks, reasons from contributions."""

import importlib
from collections.abc import Hashable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from silip_ml.ev import exposure
from silip_ml.features import (
    WEATHER_LOAD_FEATURES,
    issue_cutoff,
    load_features,
    risk_features,
    weather_at,
    weather_input,
)
from silip_ml.load.domain import history_grid
from silip_ml.readings.domain import STEPS_PER_DAY
from silip_ml.risk.domain import contribution_drivers, risk_output

NOTEBOOKS = Path(__file__).parents[2] / "notebooks"


@pytest.fixture
def notebook_features(monkeypatch):
    monkeypatch.syspath_prepend(str(NOTEBOOKS))
    return importlib.import_module("_features")


def _scoring_day(dataset) -> pd.Timestamp:
    days = dataset.load["ts"].dt.normalize().drop_duplicates().sort_values()
    return days.iloc[-3]


def _tampered(weather: pd.DataFrame, cutoff: pd.Timestamp) -> pd.DataFrame:
    """Every row a run at `cutoff` must not read is pushed 50 °C / 50 mm off."""
    later = pd.to_datetime(weather["issued_at"], utc=True) > cutoff
    future_archive = (weather["kind"] == "archive") & (
        pd.to_datetime(weather["ts"], utc=True) > cutoff
    )
    bad = (later | future_archive).to_numpy()
    assert bad.any()
    return weather.assign(
        heat_index_c=np.where(bad, weather["heat_index_c"] + 50, weather["heat_index_c"]),
        precipitation_mm=np.where(
            bad, weather["precipitation_mm"] + 50, weather["precipitation_mm"]
        ),
    )


def test_load_features_read_only_weather_issued_by_the_scoring_time(dataset):
    day = _scoring_day(dataset)
    grid = history_grid(dataset.load[dataset.load["ts"] < day])
    rows = grid.steps + np.arange(2 * STEPS_PER_DAY)  # 48 h: day two must not see later issues
    features = list(WEATHER_LOAD_FEATURES)
    honest = load_features(
        grid, rows, features, [], weather_input(dataset.weather, dataset.transformers)
    )
    tampered_rows = _tampered(dataset.weather, issue_cutoff(day))
    tampered = load_features(
        grid, rows, features, [], weather_input(tampered_rows, dataset.transformers)
    )
    np.testing.assert_array_equal(honest, tampered)
    assert np.isfinite(honest[:, 0]).all()  # every hour has a forecast issued by 00:00


def test_risk_features_read_only_weather_issued_by_the_scoring_time(dataset):
    day = _scoring_day(dataset)
    history = dataset.load[dataset.load["ts"] < day]
    forecast = dataset.load[dataset.load["ts"].dt.normalize() == day].rename(
        columns={"transformer_kw": "kw_pred"}
    )
    honest = risk_features(
        forecast,
        "kw_pred",
        dataset.transformers,
        weather_input(dataset.weather, dataset.transformers),
        history,
    )
    tampered_rows = _tampered(dataset.weather, issue_cutoff(day))
    tampered = risk_features(
        forecast,
        "kw_pred",
        dataset.transformers,
        weather_input(tampered_rows, dataset.transformers),
        history,
    )
    pd.testing.assert_series_equal(honest["heat_index_max_c"], tampered["heat_index_max_c"])
    assert honest["heat_index_max_c"].notna().all()
    assert honest["reporting_pct"].between(0, 1).all()
    assert (honest["weather_source"] == "Simulated").all()


def test_weather_features_match_the_notebook(dataset, notebook_features):
    weather = dataset.weather
    cells = np.repeat(weather["cell_id"].unique()[:1], 200)
    ts = pd.DatetimeIndex(
        pd.date_range(dataset.load["ts"].min() + pd.Timedelta(days=2), periods=200, freq="37min")
    )
    cutoff = pd.DatetimeIndex(notebook_features.issue_cutoff(ts))
    ours = weather_at(weather, cells, ts, cutoff)
    theirs = notebook_features.weather_at(weather, cells, ts, cutoff)
    for name in WEATHER_LOAD_FEATURES:
        np.testing.assert_array_equal(ours[name], theirs[name])


def test_station_counts_match_the_notebook(dataset, notebook_features):
    stations = pd.DataFrame(
        {"lat": [14.3708, 14.40, 14.3710, 15.0], "lon": [121.0498, 121.04, 121.0500, 121.0]}
    )
    ours = exposure(dataset.transformers, stations)["stations_within"].to_numpy()
    np.testing.assert_array_equal(
        ours, notebook_features.stations_within(dataset.transformers, stations)
    )


ROW: dict[Hashable, Any] = {
    "transformer_id": "T-1",
    "peak_load_pct": 1.12,
    "peak_ts": pd.Timestamp("2026-05-20 21:00", tz="Asia/Manila"),
    "mean_load_pct": 0.7,
    "hours_over_100": 2.5,
    "hours_over_110": 0.0,
    "hours_over_90": 3.0,
    "coverage_pct": 0.6,
    "rated_kva": 50.0,
    "heat_index_max_c": 42.3,
    "heat_index_max_ts": pd.Timestamp("2026-05-20 14:00", tz="Asia/Manila"),
    "ev_evening_step_kw": 3.1,
    "ev_stations_within": 4.0,
    "reporting_pct": 0.35,
    "weather_source": "Simulated",
    "is_simulated": True,
}


def test_reasons_are_the_top_three_positive_contributions():
    contributions = {
        "hours_over_110": 2.0,
        "heat_index_max_c": 1.5,
        "ev_evening_step_kw": 0.9,
        "ev_stations_within": 0.4,
        "reporting_pct": 0.8,
        "rated_kva": -1.0,
    }
    drivers = contribution_drivers(ROW, contributions)
    # hours_over_110 is 0 h: it explains nothing, so the next one moves up
    assert [d.feature for d in drivers] == [
        "heat_index_max_c",
        "ev_evening_step_kw",
        "reporting_pct",
    ]
    assert drivers[0].text == "Forecast heat index 42 °C at 14:00 (Simulated)"
    assert drivers[1].text == "Evening load up 3.1 kW vs the 3 weeks before; EV charging likely"
    assert drivers[2].text == "Only 35% of homes reporting; estimate less certain"
    output = risk_output(ROW, "Critical", drivers)
    assert output.reasons == [d.text for d in drivers]
    assert output.confidence == pytest.approx(0.35)  # share reporting, not coverage
    assert output.peak_ts is not None and output.peak_ts.hour == 21


def test_charger_reason_and_rule_fallback():
    drivers = contribution_drivers(ROW, {"ev_stations_within": 0.5, "peak_load_pct": 0.2})
    assert [d.text for d in drivers] == [
        "4 public EV chargers within 1 km (DOE)",
        "Peak forecast 112% of rating at 21:00",
    ]
    output = risk_output(
        {**ROW, "reporting_pct": float("nan")}, "OK", contribution_drivers(ROW, {"rated_kva": -0.3})
    )
    assert output.reasons[0].startswith("Peak forecast")  # no positive contribution: rule reasons
    assert output.confidence == pytest.approx(0.6)  # reporting unknown: coverage
    assert output.drivers == []
