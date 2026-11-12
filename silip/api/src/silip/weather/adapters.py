"""Weather adapters: the Open-Meteo client, the Neon cache (insert-only) and simulated forecasts."""

from __future__ import annotations

import http.client
import json
import logging
import time
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlsplit

import pandas as pd
import psycopg

from silip.weather.domain import (
    FORECAST_DAYS,
    LOCAL_TZ,
    WEATHER_COLUMNS,
    Cell,
    WeatherFetchError,
)

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT_S = 5.0
READ_TIMEOUT_S = 10.0
BUDGET_S = 30.0
BACKOFF_S = (1.0, 3.0)  # one wait before each retry: 2 retries
HOURLY = ("temperature_2m", "relative_humidity_2m", "precipitation")
HOURLY_COLUMNS = {
    "temperature_2m": "temperature_c",
    "relative_humidity_2m": "relative_humidity_pct",
    "precipitation": "precipitation_mm",
}

# (url, connect timeout s, read timeout s) -> body. Raises OSError (incl. timeouts) or HttpError.
Transport = Callable[[str, float, float], bytes]


class HttpError(Exception):
    """A non-2xx response."""

    def __init__(self, status: int) -> None:
        super().__init__(f"HTTP {status}")
        self.status = status

    @property
    def retryable(self) -> bool:
        return self.status == 429 or self.status >= 500


def http_get(url: str, connect_timeout: float, read_timeout: float) -> bytes:
    """Stdlib GET with separate connect and read timeouts (urlopen has only one)."""
    parts = urlsplit(url)
    connection_class = (
        http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
    )
    connection = connection_class(parts.netloc, timeout=connect_timeout)
    try:
        connection.connect()
        if connection.sock is not None:
            connection.sock.settimeout(read_timeout)
        path = parts.path + (f"?{parts.query}" if parts.query else "")
        connection.request("GET", path, headers={"Accept": "application/json"})
        response = connection.getresponse()
        body = response.read()
        if not 200 <= response.status < 300:
            raise HttpError(response.status)
        return body
    finally:
        connection.close()


class OpenMeteoClient:
    """One request for all cells: hourly temperature, humidity and rain for FORECAST_DAYS days."""

    def __init__(
        self,
        base_url: str,
        transport: Transport = http_get,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._base_url = base_url
        self._transport = transport
        self._sleep = sleep
        self._clock = clock

    def url(self, cells: Sequence[Cell]) -> str:
        query = {
            "latitude": ",".join(f"{cell.lat:.4f}" for cell in cells),
            "longitude": ",".join(f"{cell.lon:.4f}" for cell in cells),
            "hourly": ",".join(HOURLY),
            "forecast_days": FORECAST_DAYS,
            "timezone": LOCAL_TZ,
        }
        return f"{self._base_url}?{urlencode(query, safe=',/')}"

    def fetch(self, cells: Sequence[Cell]) -> pd.DataFrame:
        if not cells:
            return pd.DataFrame(columns=["cell_id", "lat", "lon", "ts", *HOURLY_COLUMNS.values()])
        return parse_forecast(self._get(self.url(cells)), cells)

    def _get(self, url: str) -> bytes:
        deadline = self._clock() + BUDGET_S
        waits = [*BACKOFF_S, None]  # None: no retry left
        last: Exception | None = None
        for attempt, wait in enumerate(waits, start=1):
            remaining = deadline - self._clock()
            try:
                return self._transport(
                    url, min(CONNECT_TIMEOUT_S, remaining), min(READ_TIMEOUT_S, remaining)
                )
            except HttpError as error:
                if not error.retryable:
                    raise WeatherFetchError(str(error)) from error
                last = error
            except OSError as error:  # connection refused, DNS, socket timeout
                last = error
            logger.info("open-meteo attempt %d failed: %s", attempt, type(last).__name__)
            if wait is None or self._clock() + wait >= deadline:
                break
            self._sleep(wait)
        raise WeatherFetchError(f"open-meteo failed after retries: {type(last).__name__}") from last


def parse_forecast(body: bytes, cells: Sequence[Cell]) -> pd.DataFrame:
    """Open-Meteo's response (a list for several points, an object for one), in request order.

    The provider snaps points to its grid, so rows keep the requested cell's id and point.
    Times are local (timezone=Asia/Manila) and become tz-aware via `utc_offset_seconds`.

    Raises:
        WeatherFetchError: if the body is not the expected shape.
    """
    try:
        payload: Any = json.loads(body)  # Any: untrusted JSON, checked field by field below
        locations = payload if isinstance(payload, list) else [payload]
        if len(locations) != len(cells):
            raise ValueError(f"{len(locations)} locations for {len(cells)} cells")
        frames = []
        for cell, location in zip(cells, locations, strict=True):
            hourly = location["hourly"]
            offset = timezone(timedelta(seconds=int(location.get("utc_offset_seconds", 0))))
            frame = pd.DataFrame(
                {column: pd.to_numeric(hourly[key]) for key, column in HOURLY_COLUMNS.items()}
            )
            frame.insert(0, "ts", pd.to_datetime(hourly["time"]).tz_localize(offset))
            frame.insert(0, "lon", cell.lon)
            frame.insert(0, "lat", cell.lat)
            frame.insert(0, "cell_id", cell.cell_id)
            frames.append(frame)
    except (ValueError, KeyError, TypeError) as error:
        raise WeatherFetchError(f"unreadable open-meteo response: {error}") from error
    rows = pd.concat(frames, ignore_index=True)
    rows["ts"] = rows["ts"].dt.tz_convert(LOCAL_TZ)
    return rows


INSERT_WEATHER = (
    f"INSERT INTO weather_hourly ({', '.join(WEATHER_COLUMNS)}) VALUES"  # noqa: S608  (constant columns)
    f" ({', '.join(f'%({column})s' for column in WEATHER_COLUMNS)})"
    " ON CONFLICT (cell_id, ts, kind, issued_at) DO NOTHING"
)
SELECT_LATEST = (
    "SELECT cell_id, lat, lon, ts, issued_at, kind, temperature_c::float8 AS temperature_c,"
    " relative_humidity_pct::float8 AS relative_humidity_pct,"
    " precipitation_mm::float8 AS precipitation_mm, heat_index_c::float8 AS heat_index_c,"
    " source, is_simulated FROM weather_hourly WHERE kind = 'forecast' AND issued_at = ("
    " SELECT max(issued_at) FROM weather_hourly WHERE kind = 'forecast'"
    " AND issued_at <= %(as_of)s) ORDER BY cell_id, ts"
)


class NeonWeatherStore:
    """weather_hourly, insert-only: every fetch is a new issued_at; nothing is rewritten."""

    def __init__(self, connect: Callable[[], psycopg.Connection]) -> None:
        self._connect = connect

    def insert(self, rows: pd.DataFrame) -> int:
        values = rows[WEATHER_COLUMNS].astype(object)
        records = values.where(values.notna(), None).to_dict("records")
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.executemany(INSERT_WEATHER, records)  # type: ignore[arg-type]  # constant SQL
            return max(cursor.rowcount, 0)

    def latest(self, as_of: datetime) -> pd.DataFrame:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(SELECT_LATEST, {"as_of": as_of})
            frame = pd.DataFrame(cursor.fetchall(), columns=WEATHER_COLUMNS)
        for column in ("ts", "issued_at"):
            frame[column] = pd.to_datetime(frame[column], utc=True).dt.tz_convert(LOCAL_TZ)
        return frame


SIM_FORECAST_CSV = "weather_forecast_hourly.csv"
SIM_REQUIRED = ("cell_id", "ts", "issued_at", "heat_index_c", "is_simulated")


class SimulatedWeather:
    """Reads `data/sim/weather_forecast_hourly.csv` (notebooks/00). Missing file: no forecast."""

    def __init__(self, data_dir: Path) -> None:
        self._path = data_dir / SIM_FORECAST_CSV
        self._rows: pd.DataFrame | None = None

    def _all(self) -> pd.DataFrame:
        if self._rows is None:
            self._rows = self._read()
        return self._rows

    def _read(self) -> pd.DataFrame:
        if not self._path.exists():
            logger.info("%s not found; simulated weather is missing", self._path.name)
            return pd.DataFrame(columns=WEATHER_COLUMNS)
        rows = pd.read_csv(self._path)
        missing = set(SIM_REQUIRED) - set(rows.columns)
        if missing:
            raise ValueError(f"{self._path.name} is missing columns: {sorted(missing)}")
        for column in ("ts", "issued_at"):
            rows[column] = pd.to_datetime(rows[column], utc=True).dt.tz_convert(LOCAL_TZ)
        defaults = {"kind": "forecast", "source": "simulated"}
        for column in WEATHER_COLUMNS:
            if column not in rows:
                rows[column] = defaults.get(column, float("nan"))
        return rows[WEATHER_COLUMNS]

    def latest(self, as_of: datetime) -> pd.DataFrame:
        rows = self._all()
        issued = rows.loc[(rows["kind"] == "forecast") & (rows["issued_at"] <= as_of), "issued_at"]
        if issued.empty:
            return rows.iloc[0:0]
        return rows[rows["issued_at"] == issued.max()].reset_index(drop=True)
