"""DataSource strategies: simulated CSVs, clamp readings in Neon, smart-meter intervals in Neon."""

from __future__ import annotations

from collections.abc import Callable
from functools import cached_property
from pathlib import Path
from typing import Any, ClassVar, LiteralString

import pandas as pd
import psycopg

from silip_ml.readings.dataset import Dataset, load_dataset

USAGE_DAYS = 7


class SimulatedSource:
    """Reads `data/sim`. Every account maps to the one demo household the simulator details."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir

    @cached_property
    def _data(self) -> Dataset:
        return load_dataset(self._data_dir)

    def transformers(self) -> pd.DataFrame:
        return self._data.transformers

    def load(self) -> pd.DataFrame:
        return self._data.load

    def outages(self) -> pd.DataFrame:
        return self._data.outages

    def outage_signals(self) -> pd.DataFrame:
        return self._data.signals

    def household_usage(self, sin_hash: str) -> pd.DataFrame:
        usage = self._data.households
        mine = usage[usage["sin_hash"] == sin_hash]
        since = mine["ts"].max() - pd.Timedelta(days=USAGE_DAYS)
        return mine.loc[mine["ts"] > since, ["ts", "power_kw", "is_simulated"]]

    def sin_hash_for_account(self, subject: str) -> str | None:
        households = self._data.households
        return None if households.empty else str(households["sin_hash"].iloc[0])


class _NeonSource:
    """Shared queries; subclasses differ only in where per-home kW comes from."""

    PER_HOME_KW: ClassVar[LiteralString]  # SELECT transformer_id, sin_hash, ts, kw, is_simulated

    def __init__(self, connect: Callable[[], psycopg.Connection]) -> None:
        self._connect = connect

    def _frame(self, sql: LiteralString, params: dict[str, Any] | None = None) -> pd.DataFrame:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(sql, params)
            columns = [column.name for column in cursor.description or []]
            return pd.DataFrame(cursor.fetchall(), columns=columns)

    def transformers(self) -> pd.DataFrame:
        return self._frame(
            "SELECT transformer_id, rated_kva, homes, coverage_pct, lat, lon, is_simulated FROM transformer"
        )

    def load(self) -> pd.DataFrame:
        # Measured homes only; spreading unmetered homes' kWh comes later (silip-domain skill).
        sql: LiteralString = (
            "WITH per_home AS ("  # noqa: S608  (class constant, no user input)
            + self.PER_HOME_KW
            + ") SELECT transformer_id, date_bin('15 minutes', ts, TIMESTAMPTZ '2000-01-01') AS ts,"
            " SUM(kw) AS transformer_kw, bool_or(is_simulated) AS is_simulated"
            " FROM per_home GROUP BY 1, 2 ORDER BY 1, 2"
        )
        return self._frame(sql)

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
            + ") SELECT ts, kw AS power_kw, is_simulated FROM per_home"
            " WHERE sin_hash = %(sin_hash)s AND ts > now() - interval '7 days' ORDER BY ts"
        )
        return self._frame(sql, {"sin_hash": sin_hash})

    def sin_hash_for_account(self, subject: str) -> str | None:
        found = self._frame(
            "SELECT sin_hash FROM household_account WHERE cognito_sub = %(subject)s",
            {"subject": subject},
        )
        return None if found.empty else str(found["sin_hash"].iloc[0])


class ClampSource(_NeonSource):
    """Opt-in clamp readings (`reading` table)."""

    PER_HOME_KW = "SELECT transformer_id, sin_hash, ts, power_kw AS kw, is_simulated FROM reading"


class SmartMeterSource(_NeonSource):
    """Smart-meter 15-minute energy (`smart_meter_interval` table), converted to average kW."""

    PER_HOME_KW = "SELECT transformer_id, sin_hash, ts, energy_kwh * 4 AS kw, is_simulated FROM smart_meter_interval"
