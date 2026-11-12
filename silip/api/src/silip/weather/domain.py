"""Hourly weather per grid cell: what a forecast row holds, how fresh it is, and the ports."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal, Protocol

import pandas as pd

WEATHER_STALE_H = 6  # [VERIFY] a forecast older than this is shown as stale
WEATHER_MAX_AGE_H = 24  # older than this, scoring uses the non-weather forecaster
REFRESH_EVERY = timedelta(minutes=60)  # at most one Open-Meteo request per hour
FORECAST_DAYS = 3
LOCAL_TZ = "Asia/Manila"

WEATHER_COLUMNS = [
    "cell_id",
    "lat",
    "lon",
    "ts",
    "issued_at",
    "kind",
    "temperature_c",
    "relative_humidity_pct",
    "precipitation_mm",
    "heat_index_c",
    "source",
    "is_simulated",
]

WeatherStatus = Literal["fresh", "stale", "missing"]


class WeatherFetchError(RuntimeError):
    """The weather provider failed (network, timeout, HTTP error or an unreadable body)."""


@dataclass(frozen=True)
class Cell:
    """One weather cell (silip_ml.weather.cell_id) and the point to ask the provider about."""

    cell_id: str
    lat: float
    lon: float


@dataclass(frozen=True)
class WeatherOutlook:
    """The forecast to use now. `rows` is empty when status is "missing"."""

    status: WeatherStatus
    issued_at: datetime | None
    rows: pd.DataFrame
    is_simulated: bool


def status_for(issued_at: datetime | None, now: datetime) -> WeatherStatus:
    if issued_at is None or now - issued_at > timedelta(hours=WEATHER_MAX_AGE_H):
        return "missing"
    return "stale" if now - issued_at > timedelta(hours=WEATHER_STALE_H) else "fresh"


class WeatherFetcher(Protocol):
    def fetch(self, cells: Sequence[Cell]) -> pd.DataFrame:
        """Hourly rows (cell_id, lat, lon, ts, temperature_c, relative_humidity_pct,
        precipitation_mm) for every cell. Raises WeatherFetchError."""
        ...


class WeatherReader(Protocol):
    def latest(self, as_of: datetime) -> pd.DataFrame:
        """All rows (WEATHER_COLUMNS) of the latest forecast issued at or before `as_of`."""
        ...


class WeatherStore(WeatherReader, Protocol):
    def insert(self, rows: pd.DataFrame) -> int:
        """Insert-only; returns rows added."""
        ...
