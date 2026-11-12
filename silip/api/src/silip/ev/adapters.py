"""Read the delivered EV files; keep a loader pass in memory or write it to Neon (insert-only)."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, LiteralString

import pandas as pd
import psycopg

from silip.ev.domain import (
    ADOPTION_COLUMNS,
    EXPOSURE_COLUMNS,
    STATION_COLUMNS,
    EvLoad,
)
from silip.ev.service import build_load

STATIONS_CSV = "evcs_locations.csv"
ADOPTION_CSV = "ev_adoption.csv"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_stations(data_dir: Path) -> tuple[pd.DataFrame, str]:
    """The DOE station file as delivered (all text) and its SHA-256."""
    path = data_dir / STATIONS_CSV
    return pd.read_csv(path, dtype=str, keep_default_na=False), file_sha256(path)


def read_adoption(data_dir: Path) -> pd.DataFrame | None:
    """The adoption file, or None while it has not been delivered."""
    path = data_dir / ADOPTION_CSV
    if not path.exists():
        return None
    return pd.read_csv(path, dtype={"period": str, "geography": str, "vehicle_class": str})


def load_from_files(data_dir: Path, transformers: pd.DataFrame, loaded_at: datetime) -> EvLoad:
    """One loader pass over `data_dir` (default `data/`). Never downloads anything."""
    raw, sha = read_stations(data_dir)
    return build_load(raw, sha, read_adoption(data_dir), transformers, loaded_at)


class MemoryEvStore:
    """DATA_SOURCE=simulated: the latest pass stays in memory, so the API works without Neon."""

    def __init__(self, load: EvLoad | None = None) -> None:
        self._load = load

    def write(self, load: EvLoad) -> None:
        self._load = load

    def stations(self) -> pd.DataFrame:
        # Every station ever loaded: with DO NOTHING a station keeps the sha of its first file.
        return pd.DataFrame(columns=STATION_COLUMNS) if self._load is None else self._load.stations

    def adoption(self) -> pd.DataFrame:
        return pd.DataFrame(columns=ADOPTION_COLUMNS) if self._load is None else self._load.adoption

    def exposure(self) -> pd.DataFrame:
        return pd.DataFrame(columns=EXPOSURE_COLUMNS) if self._load is None else self._load.exposure


def _insert_sql(table: LiteralString, columns: list[str], key: LiteralString) -> str:
    names = ", ".join(columns)
    values = ", ".join(f"%({column})s" for column in columns)
    return f"INSERT INTO {table} ({names}) VALUES ({values}) ON CONFLICT ({key}) DO NOTHING"  # noqa: S608  (constant names)


INSERT_STATION = _insert_sql("ev_charger", STATION_COLUMNS, "station_id")
INSERT_ADOPTION = _insert_sql(
    "ev_adoption", ADOPTION_COLUMNS, "period, geography_level, geography, metric, vehicle_class"
)
INSERT_EXPOSURE = _insert_sql(
    "transformer_ev_exposure", EXPOSURE_COLUMNS, "transformer_id, source_sha256"
)


def _records(frame: pd.DataFrame, columns: list[str]) -> list[dict[str, Any]]:
    values = frame[columns].astype(object)
    return values.where(values.notna(), None).to_dict("records")  # type: ignore[return-value]


class NeonEvStore:
    """Insert-only (the app role has SELECT, INSERT): a rerun of the same file adds nothing."""

    def __init__(self, connect: Callable[[], psycopg.Connection]) -> None:
        self._connect = connect

    def write(self, load: EvLoad) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.executemany(INSERT_STATION, _records(load.stations, STATION_COLUMNS))  # type: ignore[arg-type]  # constant SQL
            if not load.adoption.empty:
                cursor.executemany(INSERT_ADOPTION, _records(load.adoption, ADOPTION_COLUMNS))  # type: ignore[arg-type]  # constant SQL
            cursor.executemany(INSERT_EXPOSURE, _records(load.exposure, EXPOSURE_COLUMNS))  # type: ignore[arg-type]  # constant SQL

    def _frame(self, sql: LiteralString, params: dict[str, Any] | None = None) -> pd.DataFrame:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(sql, params)
            columns = [column.name for column in cursor.description or []]
            return pd.DataFrame(cursor.fetchall(), columns=columns)

    def stations(self) -> pd.DataFrame:
        # Every station ever loaded: with DO NOTHING a station keeps the sha of its first file.
        return self._frame(
            "SELECT station_id, name, region, province, city, barangay, lat, lon, source,"
            " source_sha256, loaded_at, is_simulated FROM ev_charger ORDER BY station_id"
        )

    def adoption(self) -> pd.DataFrame:
        return self._frame(
            "SELECT period, geography_level, geography, metric, vehicle_class,"
            " value::float8 AS value, unit, source_url, retrieved_at, is_simulated"
            " FROM ev_adoption ORDER BY period, geography_level, geography, metric, vehicle_class"
        )

    def exposure(self) -> pd.DataFrame:
        return self._frame(
            "SELECT transformer_id, radius_m, stations_within,"
            " nearest_station_m::float8 AS nearest_station_m, source_sha256, computed_at,"
            " is_simulated FROM transformer_ev_exposure"
            " WHERE source_sha256 = (SELECT source_sha256 FROM transformer_ev_exposure"
            " ORDER BY computed_at DESC LIMIT 1) ORDER BY transformer_id"
        )
