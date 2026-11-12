"""Refresh the forecast at most once an hour; a provider failure falls back to the stored one."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime

import pandas as pd

from silip.weather.domain import (
    OUTLOOK_HOURS,
    REFRESH_EVERY,
    WEATHER_COLUMNS,
    AreaHour,
    Cell,
    CellPeak,
    WeatherFetcher,
    WeatherFetchError,
    WeatherHour,
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


def no_forecast() -> WeatherOutlook:
    """No usable forecast: scoring falls back to the non-weather forecaster."""
    return WeatherOutlook("missing", None, pd.DataFrame(columns=WEATHER_COLUMNS), False)


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


def _ahead(rows: pd.DataFrame, now: datetime) -> pd.DataFrame:
    """Forecast hours in (now, now + OUTLOOK_HOURS]."""
    if rows.empty:
        return rows
    end = pd.Timestamp(now) + pd.Timedelta(hours=OUTLOOK_HOURS)
    return rows[(rows["ts"] > pd.Timestamp(now)) & (rows["ts"] <= end)]


def _number(value: object) -> float | None:
    return None if pd.isna(value) else round(float(value), 2)  # type: ignore[arg-type]  # scalar


def cell_hours(forecast: WeatherOutlook, cell: str, now: datetime) -> list[WeatherHour]:
    """The next OUTLOOK_HOURS for one cell, hour by hour."""
    rows = _ahead(forecast.rows, now)
    rows = rows[rows["cell_id"] == cell].sort_values("ts")
    return [
        WeatherHour(
            ts=row["ts"],
            temperature_c=_number(row["temperature_c"]),
            relative_humidity_pct=_number(row["relative_humidity_pct"]),
            precipitation_mm=_number(row["precipitation_mm"]),
            heat_index_c=_number(row["heat_index_c"]),
        )
        for row in rows.to_dict("records")
    ]


def area_hours(forecast: WeatherOutlook, cells: Sequence[Cell], now: datetime) -> list[AreaHour]:
    """Per hour, the hottest and wettest of `cells`."""
    rows = _ahead(forecast.rows, now)
    rows = rows[rows["cell_id"].isin([cell.cell_id for cell in cells])]
    if rows.empty:
        return []
    hourly = rows.groupby("ts", as_index=False)[
        ["heat_index_c", "temperature_c", "precipitation_mm"]
    ].max()
    return [
        AreaHour(
            ts=row["ts"],
            heat_index_max_c=_number(row["heat_index_c"]),
            temperature_max_c=_number(row["temperature_c"]),
            precipitation_max_mm=_number(row["precipitation_mm"]),
        )
        for row in hourly.to_dict("records")
    ]


def cell_peaks(forecast: WeatherOutlook, cells: Sequence[Cell], now: datetime) -> list[CellPeak]:
    """Each cell's hottest hour ahead (null when it has no forecast)."""
    rows = _ahead(forecast.rows, now).dropna(subset=["heat_index_c"])
    peaks = []
    for cell in cells:
        mine = rows[rows["cell_id"] == cell.cell_id].to_dict("records")
        top = max(mine, key=lambda row: row["heat_index_c"]) if mine else None
        peaks.append(
            CellPeak(
                cell_id=cell.cell_id,
                lat=cell.lat,
                lon=cell.lon,
                heat_index_max_c=None if top is None else _number(top["heat_index_c"]),
                max_at=None if top is None else top["ts"],
            )
        )
    return peaks
