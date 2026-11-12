"""DataSource strategies: simulated CSVs, and Neon tables (whole-transformer load, clamp, smart meter)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from functools import cached_property
from pathlib import Path
from typing import Any, ClassVar, LiteralString

import pandas as pd
import psycopg

from silip_ml.readings.dataset import Dataset, load_dataset

USAGE_DAYS = 7
CLAMP_COLUMNS = [
    "clamp_id",
    "transformer_id",
    "lat",
    "lon",
    "ct_model",
    "installed_at",
    "last_seen_at",
    "is_simulated",
]
LOCAL_TZ = "Asia/Manila"  # the simulator's zone; services format peak times in local hours


class SimulatedSource:
    """Reads `data/sim`. Every account maps to the one demo household the simulator details."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir

    @cached_property
    def _data(self) -> Dataset:
        return load_dataset(self._data_dir)

    def transformers(self) -> pd.DataFrame:
        return self._data.transformers

    def load(self, since: datetime | None = None) -> pd.DataFrame:
        load = self._data.load
        return load if since is None else load[load["ts"] > since]

    def latest_load_ts(self) -> pd.Timestamp | None:
        load = self._data.load
        return None if load.empty else pd.Timestamp(load["ts"].max())

    def outages(self) -> pd.DataFrame:
        return self._data.outages

    def outage_signals(self) -> pd.DataFrame:
        return self._data.signals

    def household_usage(self, sin_hash: str) -> pd.DataFrame:
        usage = self._data.households
        mine = usage[usage["sin_hash"] == sin_hash]
        since = mine["ts"].max() - pd.Timedelta(days=USAGE_DAYS)
        return mine.loc[mine["ts"] > since, ["ts", "power_kw", "is_simulated"]]

    @cached_property
    def _clamps(self) -> pd.DataFrame:
        # load_dataset (ml/) does not read clamps.csv; sims made before clamps existed lack it.
        path = self._data_dir / "clamps.csv"
        if not path.exists():
            return pd.DataFrame(columns=CLAMP_COLUMNS)
        clamps = pd.read_csv(path)
        places = pd.read_csv(self._data_dir / "sin_map.csv").dropna(subset=["lat", "lon"])
        # The join on sin_hash stays here, so no caller ever sees it.
        joined = clamps.merge(places, on="sin_hash", suffixes=("", "_household"))
        # Simulated if either the device row or the household row is.
        joined["is_simulated"] = joined["is_simulated"] | joined["is_simulated_household"]
        for column in ("installed_at", "last_seen_at"):
            joined[column] = pd.to_datetime(joined[column], utc=True).dt.tz_convert(LOCAL_TZ)
        return joined[CLAMP_COLUMNS]

    def clamps(self) -> pd.DataFrame:
        return self._clamps

    def sin_hash_for_account(self, subject: str) -> str | None:
        households = self._data.households
        return None if households.empty else str(households["sin_hash"].iloc[0])


BUCKET: LiteralString = "date_bin('15 minutes', ts, TIMESTAMPTZ '2000-01-01')"


def _after(column: LiteralString) -> LiteralString:
    """SQL: `column > %(since)s`, or true when since is null (load everything)."""
    return "(%(since)s::timestamptz IS NULL OR " + column + " > %(since)s::timestamptz)"


def _db_time(since: datetime | None) -> datetime | None:
    # pd.Timestamp is a datetime subclass; hand psycopg the plain type.
    return None if since is None else pd.Timestamp(since).to_pydatetime()


class _NeonSource:
    """Shared queries; subclasses differ only in where per-home kW comes from."""

    PER_HOME_KW: ClassVar[LiteralString]  # SELECT transformer_id, sin_hash, ts, kw, is_simulated

    def __init__(self, connect: Callable[[], psycopg.Connection]) -> None:
        self._connect = connect

    def _frame(self, sql: LiteralString, params: dict[str, Any] | None = None) -> pd.DataFrame:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(sql, params)
            columns = [column.name for column in cursor.description or []]
            frame = pd.DataFrame(cursor.fetchall(), columns=columns)
        for column in frame.columns:
            if isinstance(frame[column].dtype, pd.DatetimeTZDtype):
                frame[column] = frame[column].dt.tz_convert(LOCAL_TZ)
        return frame

    def transformers(self) -> pd.DataFrame:
        # numeric -> float8, else psycopg returns Decimal and numpy math fails.
        return self._frame(
            "SELECT transformer_id, rated_kva::float8 AS rated_kva, homes,"
            " coverage_pct::float8 AS coverage_pct, lat, lon, is_simulated FROM transformer"
            # The live-demo bench rig (silip.shared.bench) is not part of the city.
            " WHERE transformer_id NOT LIKE 'BENCH-%%'"
        )

    def _latest(self, sql: LiteralString) -> pd.Timestamp | None:
        latest = self._frame(sql)["ts"].iloc[0]
        return None if pd.isna(latest) else pd.Timestamp(latest).tz_convert(LOCAL_TZ)

    def load(self, since: datetime | None = None) -> pd.DataFrame:
        # Measured homes only; spreading unmetered homes' kWh comes later (silip-domain skill).
        # The WHERE only narrows the scan; HAVING keeps whole 15-minute buckets after `since`.
        sql: LiteralString = (
            "WITH per_home AS ("  # noqa: S608  (class constant, no user input)
            + self.PER_HOME_KW
            + "), intervals AS (SELECT transformer_id, sin_hash, "
            + BUCKET
            + " AS ts, avg(kw) AS kw, bool_or(is_simulated) AS is_simulated"
            " FROM per_home WHERE (%(since)s::timestamptz IS NULL"
            " OR ts > %(since)s::timestamptz - interval '15 minutes')"
            " GROUP BY 1, 2, 3)"
            " SELECT transformer_id, ts, SUM(kw) AS transformer_kw,"
            " bool_or(is_simulated) AS is_simulated FROM intervals"
            " WHERE " + _after("ts") + " GROUP BY 1, 2 ORDER BY 1, 2"
        )
        return self._frame(sql, {"since": _db_time(since)})

    def latest_load_ts(self) -> pd.Timestamp | None:
        sql: LiteralString = (
            "WITH per_home AS ("  # noqa: S608  (class constant, no user input)
            + self.PER_HOME_KW
            + ") SELECT date_bin('15 minutes', max(ts), TIMESTAMPTZ '2000-01-01') AS ts"
            " FROM per_home"
        )
        return self._latest(sql)

    def outages(self) -> pd.DataFrame:
        return self._frame(
            "SELECT o.outage_id, o.transformer_id, o.start_ts, o.cause, o.duration_min,"
            " t.lat, t.lon, o.is_simulated FROM outage o JOIN transformer t USING (transformer_id)"
        )

    def outage_signals(self) -> pd.DataFrame:
        return self._frame("SELECT outage_id, kind, ts, lat, lon FROM outage_signal")

    def household_usage(self, sin_hash: str) -> pd.DataFrame:
        sql: LiteralString = (
            "WITH per_home AS ("  # noqa: S608  (class constant, no user input)
            + self.PER_HOME_KW
            + ") SELECT date_bin('15 minutes', ts, TIMESTAMPTZ '2000-01-01') AS ts,"
            " avg(kw)::float8 AS power_kw, bool_or(is_simulated) AS is_simulated FROM per_home"
            " WHERE sin_hash = %(sin_hash)s"
            # Week before the household's latest reading (like SimulatedSource), not now().
            " AND ts > (SELECT max(ts) FROM per_home WHERE sin_hash = %(sin_hash)s)"
            " - make_interval(days => %(days)s) GROUP BY 1 ORDER BY ts"
        )
        return self._frame(sql, {"sin_hash": sin_hash, "days": USAGE_DAYS})

    def clamps(self) -> pd.DataFrame:
        # Joined server-side so sin_hash never leaves the database; the map needs a place.
        return self._frame(
            "SELECT c.clamp_id, h.transformer_id, h.lat, h.lon, c.ct_model, c.installed_at,"
            " c.last_seen_at, (c.is_simulated OR h.is_simulated) AS is_simulated"
            " FROM clamp c JOIN household h USING (sin_hash)"
            " WHERE h.lat IS NOT NULL AND h.lon IS NOT NULL ORDER BY c.clamp_id"
        )

    def sin_hash_for_account(self, subject: str) -> str | None:
        found = self._frame(
            "SELECT sin_hash FROM household_account WHERE cognito_sub = %(subject)s",
            {"subject": subject},
        )
        return None if found.empty else str(found["sin_hash"].iloc[0])


class ClampSource(_NeonSource):
    """Opt-in clamp readings (`reading` table)."""

    # Bench rig readings (BENCH-*) feed only the /demo page, never city load or scoring.
    PER_HOME_KW = (
        "SELECT transformer_id, sin_hash, ts, power_kw AS kw, is_simulated FROM reading"
        " WHERE transformer_id NOT LIKE 'BENCH-%%'"
    )


class SmartMeterSource(_NeonSource):
    """Smart-meter 15-minute energy (`smart_meter_interval` table), converted to average kW."""

    PER_HOME_KW = "SELECT transformer_id, sin_hash, ts, energy_kwh * 4 AS kw, is_simulated FROM smart_meter_interval"


class NeonSource(_NeonSource):
    """What `load_sim` (or the team) puts in Neon: whole-transformer kW plus per-home kW.

    Own tables instead of `reading`, because a transformer total and a bare per-home kW have no
    voltage/current to fill `reading`'s NOT NULL columns.
    """

    PER_HOME_KW = (
        "SELECT transformer_id, sin_hash, ts, power_kw AS kw, is_simulated FROM household_load"
    )

    def load(self, since: datetime | None = None) -> pd.DataFrame:
        sql: LiteralString = (
            "SELECT transformer_id, ts, transformer_kw::float8 AS transformer_kw, is_simulated"  # noqa: S608  (constants only)
            " FROM transformer_load WHERE " + _after("ts") + " ORDER BY transformer_id, ts"
        )
        return self._frame(sql, {"since": _db_time(since)})

    def latest_load_ts(self) -> pd.Timestamp | None:
        return self._latest("SELECT max(ts) AS ts FROM transformer_load")
