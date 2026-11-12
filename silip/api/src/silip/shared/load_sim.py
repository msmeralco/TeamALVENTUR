"""Load `data/sim` CSVs into Neon for DATA_SOURCE=neon: `python -m silip.shared.load_sim [dir]`.

Idempotent: rows go through COPY into a temp table, then INSERT ... ON CONFLICT DO NOTHING, so a
rerun adds nothing and never changes a row already there (including its `is_simulated`). The one
exception is `fill_nulls`: columns added later are filled where an existing row still has null.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import psycopg
from psycopg import sql

from silip.shared.config import ApiSettings, get_settings
from silip.shared.db import CONNECT_TIMEOUT_S, direct_url

SIN_HASH = r"[0-9a-f]{64}"


class NotSimulatedError(ValueError):
    """A CSV row is not simulated; this loader only labels and loads simulated data."""


@dataclass(frozen=True)
class Table:
    """One Neon table filled from one CSV. `columns` are shared by the CSV and the table."""

    name: str
    csv: str
    columns: tuple[str, ...]
    integers: tuple[str, ...] = ()
    # outage_signal has no key, so a rerun skips rows that already match on these columns.
    match_on: tuple[str, ...] = ()
    # Columns added after rows were first loaded: a rerun fills them where they are still null.
    fill_nulls: tuple[str, ...] = ()


# Parents before children (foreign keys).
TABLES = (
    Table(
        "transformer",
        "transformers.csv",
        ("transformer_id", "rated_kva", "homes", "coverage_pct", "lat", "lon", "osm_node_id")
        + ("is_simulated",),
        integers=("homes", "osm_node_id"),
    ),
    Table(
        "household",
        "sin_map.csv",
        ("sin_hash", "transformer_id", "has_clamp", "lat", "lon", "osm_way_id", "is_simulated"),
        integers=("osm_way_id",),
        fill_nulls=("lat", "lon", "osm_way_id"),
    ),
    Table(
        "clamp",
        "clamps.csv",
        ("clamp_id", "sin_hash", "ct_model", "installed_at", "last_seen_at", "is_simulated"),
    ),
    Table(
        "transformer_load",
        "transformer_load_15m.csv",
        ("transformer_id", "ts", "transformer_kw", "is_simulated"),
    ),
    Table(
        "household_load",
        "household_load_15m.csv",
        ("sin_hash", "transformer_id", "ts", "power_kw", "is_simulated"),
    ),
    Table(
        "outage",
        "outages.csv",
        ("outage_id", "transformer_id", "start_ts", "cause", "duration_min", "is_simulated"),
        integers=("duration_min",),
    ),
    Table(
        "outage_signal",
        "outage_signals.csv",
        ("outage_id", "kind", "ts", "lat", "lon", "is_simulated"),
        match_on=("outage_id", "kind", "ts"),
    ),
)


def read_table(data_dir: Path, table: Table) -> pd.DataFrame:
    """The CSV's columns for `table` as Python values (None for blanks); timestamps stay text.

    Raises:
        ValueError: if `is_simulated` is not a boolean or a `sin_hash` is not a 64-hex hash.
        NotSimulatedError: if any row has `is_simulated` False (real data needs its own path).
    """
    text_columns = {
        name: str for name in ("ts", "start_ts", "installed_at", "last_seen_at", "sin_hash")
    }
    frame = pd.read_csv(data_dir / table.csv, usecols=list(table.columns), dtype=text_columns)
    frame = frame[list(table.columns)]
    if not pd.api.types.is_bool_dtype(frame["is_simulated"]):
        raise ValueError(f"{table.csv}: is_simulated must be True/False")
    if not frame["is_simulated"].all():
        raise NotSimulatedError(f"{table.csv}: every row must have is_simulated=True")
    if "sin_hash" in frame and not frame["sin_hash"].str.fullmatch(SIN_HASH, na=False).all():
        raise ValueError(f"{table.csv}: every sin_hash must be a salted 64-hex hash")
    values = frame.astype(object).where(frame.notna(), None)
    for column in table.integers:
        values[column] = [None if value is None else int(value) for value in values[column]]
    values["is_simulated"] = values["is_simulated"].map(bool)
    return values


def _insert(cursor: psycopg.Cursor, data_dir: Path, table: Table) -> int:
    staging = sql.Identifier(f"staging_{table.name}")
    target = sql.Identifier(table.name)
    columns = sql.SQL(", ").join(map(sql.Identifier, table.columns))
    cursor.execute(sql.SQL("CREATE TEMP TABLE {} (LIKE {}) ON COMMIT DROP").format(staging, target))
    with cursor.copy(sql.SQL("COPY {} ({}) FROM STDIN").format(staging, columns)) as copy:
        for row in read_table(data_dir, table).itertuples(index=False, name=None):
            copy.write_row(row)
    if table.match_on:
        same = sql.SQL(" AND ").join(
            sql.SQL("t.{0} = s.{0}").format(sql.Identifier(c)) for c in table.match_on
        )
        guard = sql.SQL("WHERE NOT EXISTS (SELECT 1 FROM {} t WHERE {})").format(target, same)
    elif table.fill_nulls:
        key = sql.Identifier(table.columns[0])
        fills = sql.SQL(", ").join(
            sql.SQL("{0} = COALESCE(t.{0}, EXCLUDED.{0})").format(sql.Identifier(c))
            for c in table.fill_nulls
        )
        missing = sql.SQL(" OR ").join(
            # Only where a value would actually change, so a rerun writes and counts nothing.
            sql.SQL("(t.{0} IS NULL AND EXCLUDED.{0} IS NOT NULL)").format(sql.Identifier(c))
            for c in table.fill_nulls
        )
        guard = sql.SQL("ON CONFLICT ({}) DO UPDATE SET {} WHERE {}").format(key, fills, missing)
    else:
        guard = sql.SQL("ON CONFLICT DO NOTHING")
    query = sql.SQL(
        "INSERT INTO {target} AS t ({columns}) SELECT {columns} FROM {staging} s {guard}"
    )
    cursor.execute(query.format(target=target, columns=columns, staging=staging, guard=guard))
    return cursor.rowcount  # inserted rows, plus rows whose null columns `fill_nulls` filled


def load(data_dir: Path, settings: ApiSettings) -> dict[str, int]:
    """Load every table in one transaction; returns rows inserted or filled per table."""
    inserted: dict[str, int] = {}
    with (
        psycopg.connect(direct_url(settings), connect_timeout=CONNECT_TIMEOUT_S) as connection,
        connection.cursor() as cursor,
    ):
        for table in TABLES:
            inserted[table.name] = _insert(cursor, data_dir, table)
    return inserted


if __name__ == "__main__":
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else "data/sim")
    for name, count in load(folder, get_settings()).items():
        print(f"{name}: {count} rows inserted or filled")
