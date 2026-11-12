"""Hourly weather per grid cell: what a forecast row holds, how fresh it is, and the ports."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

import pandas as pd
from pydantic import BaseModel, Field

from silip.shared.scores.domain import WeatherStatus

WEATHER_STALE_H = 6  # [VERIFY] a forecast older than this is shown as stale
WEATHER_MAX_AGE_H = 24  # older than this, scoring uses the non-weather forecaster
REFRESH_EVERY = timedelta(minutes=60)  # at most one Open-Meteo request per hour
FORECAST_DAYS = 3
OUTLOOK_HOURS = 48  # what the dashboard shows ahead
# The provider label shown beside every weather number.
SOURCE_LABELS = {"simulated": "Simulated", "open_meteo": "Open-Meteo"}
LOCAL_TZ = "Asia/Manila"
# Open-Meteo is read on the wall clock, so with simulated load the two cover different days.
LIVE_ON_SIMULATED_NOTE = "Live forecast; load data is simulated"

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


class WeatherHour(BaseModel):
    """One forecast hour in one weather cell."""

    ts: datetime
    temperature_c: float | None
    relative_humidity_pct: float | None
    precipitation_mm: float | None
    heat_index_c: float | None


class AreaHour(BaseModel):
    """One forecast hour across the cells in view: the hottest and wettest cell."""

    ts: datetime
    heat_index_max_c: float | None
    temperature_max_c: float | None
    precipitation_max_mm: float | None


class CellPeak(BaseModel):
    """A weather cell's hottest forecast hour in the outlook window."""

    cell_id: str
    lat: float
    lon: float
    heat_index_max_c: float | None
    max_at: datetime | None


class AreaOutlook(BaseModel):
    """The next OUTLOOK_HOURS of forecast for the transformers in view."""

    issued_at: datetime | None
    status: WeatherStatus
    source: str
    hours: list[AreaHour]
    cells: list[CellPeak]
    is_simulated: bool
    note: str | None = Field(
        default=None, description="Set when a live forecast sits beside simulated load data"
    )
