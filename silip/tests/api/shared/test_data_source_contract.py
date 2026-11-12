"""Every DataSource strategy returns the same columns and invariants (Liskov contract).

`simulated` always runs. `neon` runs only when DATABASE_URL or DATABASE_POOLER_URL is set in the
environment, against whatever `python -m silip.shared.load_sim` loaded.
"""

import os
from collections.abc import Callable

import pandas as pd
import pytest

from silip.shared.config import ApiSettings
from silip.shared.db import connect
from silip.shared.readings.adapters import NeonSource, SimulatedSource
from silip.shared.readings.domain import DataSource

USAGE_DAYS = 7
NEON_URL_SET = bool(os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_POOLER_URL"))

COLUMNS = {
    "transformers": ["transformer_id", "rated_kva", "homes", "coverage_pct", "lat", "lon"],
    "load": ["transformer_id", "ts", "transformer_kw"],
    "outages": ["outage_id", "transformer_id", "start_ts", "cause", "duration_min", "lat", "lon"],
    "outage_signals": ["outage_id", "kind", "ts", "lat", "lon"],
    "clamps": [
        "clamp_id",
        "transformer_id",
        "lat",
        "lon",
        "ct_model",
        "installed_at",
        "last_seen_at",
    ],
}
NUMERIC = {"rated_kva", "homes", "coverage_pct", "lat", "lon", "transformer_kw", "duration_min"}
TIMES = {"ts", "start_ts", "installed_at", "last_seen_at"}
WITH_FLAG = ["transformers", "load", "outages", "clamps"]


def _neon() -> tuple[DataSource, str]:
    settings = ApiSettings()
    source = NeonSource(lambda: connect(settings))
    with connect(settings) as connection:
        row = connection.execute(
            "SELECT sin_hash FROM household_load ORDER BY sin_hash LIMIT 1"
        ).fetchone()
    assert row is not None, "household_load is empty; run python -m silip.shared.load_sim"
    return source, str(row[0])


@pytest.fixture(
    params=[
        "simulated",
        pytest.param(
            "neon",
            marks=[
                pytest.mark.integration,
                pytest.mark.skipif(not NEON_URL_SET, reason="needs DATABASE_URL"),
            ],
        ),
    ]
)
def source_and_home(request, sim_dir, dataset) -> tuple[DataSource, str]:
    builders: dict[str, Callable[[], tuple[DataSource, str]]] = {
        "simulated": lambda: (
            SimulatedSource(sim_dir),
            str(dataset.households["sin_hash"].iloc[0]),
        ),
        "neon": _neon,
    }
    return builders[request.param]()


def test_tables_have_the_contract_columns_and_types(source_and_home):
    source, _ = source_and_home
    for table, columns in COLUMNS.items():
        frame: pd.DataFrame = getattr(source, table)()
        assert not frame.empty, table
        assert set(columns) <= set(frame.columns), table
        for column in columns:
            if column in NUMERIC:
                assert pd.api.types.is_numeric_dtype(frame[column]), (table, column)
            if column in TIMES:
                assert isinstance(frame[column].dtype, pd.DatetimeTZDtype), (table, column)
                assert frame[column].dropna().iloc[0].utcoffset() == pd.Timedelta(hours=8), (
                    table,
                    column,
                )
    for table in WITH_FLAG:
        assert pd.api.types.is_bool_dtype(getattr(source, table)()["is_simulated"]), table


def test_every_transformer_has_load(source_and_home):
    source, _ = source_and_home
    with_load = set(source.load()["transformer_id"])
    assert set(source.transformers()["transformer_id"]) <= with_load


def test_usage_is_the_last_week_of_the_household(source_and_home):
    source, sin_hash = source_and_home
    usage = source.household_usage(sin_hash)
    assert list(usage.columns) == ["ts", "power_kw", "is_simulated"]
    assert 0 < len(usage) <= USAGE_DAYS * 96
    assert usage["ts"].max() - usage["ts"].min() < pd.Timedelta(days=USAGE_DAYS)
    assert pd.api.types.is_bool_dtype(usage["is_simulated"])


def test_clamps_carry_no_household_identity(source_and_home):
    source, _ = source_and_home
    clamps = source.clamps()
    assert "sin_hash" not in clamps.columns
    assert set(clamps["transformer_id"]) <= set(source.transformers()["transformer_id"])


def test_load_since_keeps_later_rows_and_latest_is_the_data_clock(source_and_home):
    source, _ = source_and_home
    load = source.load()
    latest = source.latest_load_ts()
    assert latest is not None and latest == load["ts"].max()
    assert latest.utcoffset() == pd.Timedelta(hours=8)
    since = latest - pd.Timedelta(hours=48)
    recent = source.load(since=since)
    assert not recent.empty and (recent["ts"] > since).all()
    assert len(recent) == int((load["ts"] > since).sum())
