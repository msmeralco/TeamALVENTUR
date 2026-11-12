"""Clean the delivered EV files and join stations to transformers. Pure: frames in, frames out."""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from silip.ev.domain import (
    ADOPTION_COLUMNS,
    ADOPTION_KEY,
    ADOPTION_METRICS,
    STATION_COLUMNS,
    STATION_SOURCE,
    Adoption,
    AdoptionPoint,
    AdoptionScenario,
    Charger,
    EvLoad,
    TransformerEv,
)
from silip.shared.geo import BoundingBox, within
from silip_ml.ev import EV_STATION_RADIUS_M, exposure, haversine_m, normalise_stations


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


def _text(value: object) -> str | None:
    return None if value is None or value is pd.NA or value != value else str(value)  # NaN != NaN


def chargers(stations: pd.DataFrame, box: BoundingBox | None) -> list[Charger]:
    """DOE stations inside `box` (all when None)."""
    return [
        Charger(
            station_id=row["station_id"],
            name=row["name"],
            lat=float(row["lat"]),
            lon=float(row["lon"]),
            barangay=_text(row["barangay"]),
            city=_text(row["city"]),
        )
        for row in within(stations, box).to_dict("records")
    ]


def adoption(rows: pd.DataFrame) -> Adoption:
    """The adoption series as delivered, or `not_loaded` while the file is missing."""
    if rows.empty:
        return Adoption(status="not_loaded", series=[], source_url=None, is_simulated=False)
    urls = rows["source_url"].dropna()
    return Adoption(
        status="loaded",
        series=[
            AdoptionPoint(**{str(k): row[k] for k in AdoptionPoint.model_fields})
            for row in rows.to_dict("records")
        ],
        source_url=str(urls.iloc[0]) if not urls.empty else None,
        is_simulated=bool(rows["is_simulated"].any()),
    )


def adoption_scenario(rows: pd.DataFrame) -> AdoptionScenario | None:
    """The newest period's first figure (national level when there is one). [VERIFY] which
    metric and geography planners want once the adoption file is delivered."""
    if rows.empty:
        return None
    latest = rows[rows["period"] == rows["period"].max()]
    national = latest[latest["geography_level"] == "national"]
    row = (national if not national.empty else latest).iloc[0]
    return AdoptionScenario(
        period=str(row["period"]),
        geography=str(row["geography"]),
        metric=str(row["metric"]),
        vehicle_class=str(row["vehicle_class"]),
        value=float(row["value"]),
        unit=str(row["unit"]),
        source_url=_text(row["source_url"]),
    )


def transformer_ev(
    lat: float,
    lon: float,
    stations: pd.DataFrame,
    adoption_rows: pd.DataFrame,
    radius_m: float = EV_STATION_RADIUS_M,
) -> TransformerEv:
    """Stations within `radius_m` of one transformer site, nearest first."""
    if stations.empty:
        near, nearest = stations, None
    else:
        distances = haversine_m(
            np.array([lat]),
            np.array([lon]),
            stations["lat"].to_numpy(float),
            stations["lon"].to_numpy(float),
        )[0]
        order = np.argsort(distances)
        near = stations.iloc[order[distances[order] <= radius_m]]
        nearest = round(float(distances.min()), 1)
    return TransformerEv(
        stations_within=len(near),
        nearest_station_m=nearest,
        radius_m=int(radius_m),
        stations=chargers(near, None),
        adoption_scenario=adoption_scenario(adoption_rows),
    )
