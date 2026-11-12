"""Clean the delivered EV files and join stations to transformers. Pure: frames in, frames out."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from silip.ev.domain import (
    ADOPTION_COLUMNS,
    ADOPTION_KEY,
    ADOPTION_METRICS,
    STATION_COLUMNS,
    STATION_SOURCE,
    EvLoad,
)
from silip_ml.ev import EV_STATION_RADIUS_M, exposure, normalise_stations


def clean_stations(
    raw: pd.DataFrame, source_sha256: str, loaded_at: datetime
) -> tuple[pd.DataFrame, int, int]:
    """Stations in snake_case inside the Philippines, one row per station_id.

    Returns (stations, dropped_outside_ph, duplicates).

    Raises:
        ValueError: if the delivered header lacks a required column.
    """
    frame, dropped, duplicates = normalise_stations(raw)
    frame["source"] = STATION_SOURCE
    frame["source_sha256"] = source_sha256
    frame["loaded_at"] = loaded_at
    frame["is_simulated"] = False
    return frame[STATION_COLUMNS], dropped, duplicates


def clean_adoption(raw: pd.DataFrame) -> pd.DataFrame:
    """Adoption rows with the fixed schema, one per key.

    Raises:
        ValueError: on missing columns, an unknown metric, a non-numeric value or a duplicate key.
    """
    missing = set(ADOPTION_COLUMNS) - set(raw.columns)
    if missing:
        raise ValueError(f"ev_adoption.csv is missing columns: {sorted(missing)}")
    frame = raw[ADOPTION_COLUMNS].copy()
    unknown = set(frame["metric"]) - ADOPTION_METRICS
    if unknown:
        raise ValueError(f"ev_adoption.csv has unknown metrics: {sorted(map(str, unknown))}")
    frame["value"] = pd.to_numeric(frame["value"], errors="raise")
    frame["retrieved_at"] = pd.to_datetime(frame["retrieved_at"], utc=True)
    if frame.duplicated(ADOPTION_KEY).any():
        raise ValueError("ev_adoption.csv has duplicate (period, geography, metric, class) rows")
    if not pd.api.types.is_bool_dtype(frame["is_simulated"]):
        raise ValueError("ev_adoption.csv: is_simulated must be True/False")
    return frame.reset_index(drop=True)


def build_load(
    raw_stations: pd.DataFrame,
    source_sha256: str,
    raw_adoption: pd.DataFrame | None,
    transformers: pd.DataFrame,
    loaded_at: datetime,
    radius_m: float = EV_STATION_RADIUS_M,
) -> EvLoad:
    """One loader pass. `raw_adoption` is None while the adoption file has not been delivered.

    Exposure rows are simulated when their transformer is (stations themselves are real).
    """
    stations, dropped, duplicates = clean_stations(raw_stations, source_sha256, loaded_at)
    adoption = (
        pd.DataFrame(columns=ADOPTION_COLUMNS)
        if raw_adoption is None
        else clean_adoption(raw_adoption)
    )
    joined = exposure(transformers, stations, radius_m)
    joined["source_sha256"] = source_sha256
    joined["computed_at"] = loaded_at
    joined["is_simulated"] = transformers["is_simulated"].astype(bool).to_numpy()
    return EvLoad(
        stations=stations,
        adoption=adoption,
        exposure=joined,
        rows_read=len(raw_stations),
        dropped_outside_ph=dropped,
        duplicates=duplicates,
        source_sha256=source_sha256,
        adoption_status="not_loaded" if raw_adoption is None else "loaded",
        loaded_at=loaded_at,
    )
