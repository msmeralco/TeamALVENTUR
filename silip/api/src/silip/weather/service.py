"""Refresh the forecast at most once an hour; a provider failure falls back to the stored one."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime

import pandas as pd

from silip.weather.domain import (
    REFRESH_EVERY,
    WEATHER_COLUMNS,
    Cell,
    WeatherFetcher,
    WeatherFetchError,
    WeatherOutlook,
    WeatherReader,
    WeatherStore,
    status_for,
)
from silip_ml.weather import cell_id, heat_index_c

logger = logging.getLogger(__name__)


def cells_for(transformers: pd.DataFrame) -> list[Cell]:
    """One cell per occupied grid cell, asked about at the mean of its transformers' sites."""
    cells = transformers[["lat", "lon"]].copy()
    cells["cell_id"] = [
        cell_id(lat, lon) for lat, lon in zip(cells["lat"], cells["lon"], strict=True)
    ]
    means = cells.groupby("cell_id", sort=True)[["lat", "lon"]].mean()
    return [
        Cell(str(cell), round(float(lat), 4), round(float(lon), 4))
        for cell, lat, lon in means.itertuples(name=None)
    ]


def outlook(reader: WeatherReader, now: datetime) -> WeatherOutlook:
    """The latest stored forecast at `now`, labeled fresh, stale or missing by its age."""
    rows = reader.latest(now)
    issued_at = None if rows.empty else pd.Timestamp(rows["issued_at"].max()).to_pydatetime()
    status = status_for(issued_at, now)
    if status == "missing":
        rows = rows.iloc[0:0]
    simulated = bool(rows["is_simulated"].any()) if not rows.empty else False
    return WeatherOutlook(status, issued_at, rows, simulated)


def forecast_rows(fetched: pd.DataFrame, issued_at: datetime) -> pd.DataFrame:
    """Provider rows as weather_hourly rows issued at `issued_at`, with the NOAA heat index."""
    rows = fetched.copy()
    rows["issued_at"] = issued_at
    rows["kind"] = "forecast"
    rows["heat_index_c"] = heat_index_c(
        rows["temperature_c"].to_numpy(float), rows["relative_humidity_pct"].to_numpy(float)
    )
    rows["source"] = "open-meteo"
    rows["is_simulated"] = False
    return rows[WEATHER_COLUMNS]


def refresh(
    cells: Sequence[Cell], now: datetime, fetcher: WeatherFetcher, store: WeatherStore
) -> WeatherOutlook:
    """Fetch and store a new forecast unless one was issued within REFRESH_EVERY.

    Never raises for a provider failure: it logs and returns the stored forecast instead.
    """
    current = outlook(store, now)
    if current.issued_at is not None and now - current.issued_at < REFRESH_EVERY:
        return current
    try:
        fetched = fetcher.fetch(cells)
    except WeatherFetchError as error:
        logger.warning("weather fetch failed (%s); using the stored forecast", error)
        return current
    store.insert(forecast_rows(fetched, now))
    return outlook(store, now)
