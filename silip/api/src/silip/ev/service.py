"""Clean the delivered EV files and join stations to transformers. Pure: frames in, frames out."""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from silip.ev.domain import (
    ADOPTION_COLUMNS,
    ADOPTION_KEY,
    ADOPTION_METRICS,
    PLUG_COLUMNS,
    STATION_COLUMNS,
    STATION_DETAIL_COLUMNS,
    STATION_SOURCE,
    Adoption,
    AdoptionPoint,
    AdoptionScenario,
    Charger,
    EvLoad,
    TransformerEv,
)
from silip.shared.geo import BoundingBox, within
from silip_ml.ev import (
    EV_STATION_RADIUS_M,
    exposure,
    haversine_m,
    normalise_details,
    normalise_stations,
)


def clean_stations(
    raw: pd.DataFrame, source_sha256: str, loaded_at: datetime
) -> tuple[pd.DataFrame, int, int]:
    """Stations in snake_case inside the Philippines, one row per station_id.

    Returns (stations, dropped_outside_ph, duplicates).

    Raises:
        ValueError: if the delivered header lacks a required column.
    """
    frame, dropped, duplicates = normalise_stations(raw)
    for column in STATION_DETAIL_COLUMNS:
        frame[column] = None
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
    raw_detail: pd.DataFrame | None = None,
    raw_plugs: pd.DataFrame | None = None,
    exposure_sha256: str | None = None,
) -> EvLoad:
    """One loader pass. `raw_adoption` is None while the adoption file has not been delivered;
    `raw_detail` and `raw_plugs` are None until the DOE station detail has been delivered.

    Exposure rows are simulated when their transformer is (stations themselves are real).
    `exposure_sha256` (default `source_sha256`) names the set of files the exposure came from.
    """
    stations, dropped, duplicates = clean_stations(raw_stations, source_sha256, loaded_at)
    plugs = pd.DataFrame(columns=PLUG_COLUMNS)
    unmatched = orphans = 0
    if raw_detail is not None:
        details, plug_rows, unmatched, orphans = normalise_details(
            raw_detail, raw_plugs, stations["station_id"]
        )
        stations = stations.drop(columns=STATION_DETAIL_COLUMNS).merge(
            details, on="station_id", how="left"
        )[STATION_COLUMNS]
        plugs = plug_rows.assign(
            source_sha256=exposure_sha256 or source_sha256,
            loaded_at=loaded_at,
            is_simulated=False,
        )[PLUG_COLUMNS]
    adoption = (
        pd.DataFrame(columns=ADOPTION_COLUMNS)
        if raw_adoption is None
        else clean_adoption(raw_adoption)
    )
    near = stations if raw_detail is not None else stations.drop(columns=STATION_DETAIL_COLUMNS)
    joined = exposure(transformers, near, radius_m)
    joined["source_sha256"] = exposure_sha256 or source_sha256
    joined["computed_at"] = loaded_at
    joined["is_simulated"] = transformers["is_simulated"].astype(bool).to_numpy()
    return EvLoad(
        stations=stations,
        plugs=plugs,
        adoption=adoption,
        exposure=joined,
        rows_read=len(raw_stations),
        dropped_outside_ph=dropped,
        duplicates=duplicates,
        source_sha256=source_sha256,
        exposure_sha256=exposure_sha256 or source_sha256,
        adoption_status="not_loaded" if raw_adoption is None else "loaded",
        loaded_at=loaded_at,
        details_matched=int(stations["doe_station_number"].notna().sum()),
        details_unmatched=unmatched,
        plugs_without_station=orphans,
    )


def _text(value: object) -> str | None:
    return None if value is None or value is pd.NA or value != value else str(value)  # NaN != NaN


def _missing(value: object) -> bool:
    return value is None or value is pd.NA or value != value  # NaN != NaN


def _int(value: object) -> int | None:
    return None if _missing(value) else int(value)  # type: ignore[arg-type]  # a number here


def _float(value: object) -> float | None:
    return None if _missing(value) else float(value)  # type: ignore[arg-type]  # a number here


def chargers(stations: pd.DataFrame, box: BoundingBox | None) -> list[Charger]:
    """DOE stations inside `box` (all when None), with the DOE detail when it has been loaded.

    Only these public site fields are returned; DOE contact fields are never loaded."""
    return [
        Charger(
            station_id=row["station_id"],
            name=row["name"],
            lat=float(row["lat"]),
            lon=float(row["lon"]),
            barangay=_text(row["barangay"]),
            city=_text(row["city"]),
            classification=_text(row.get("classification")),
            n_ac=_int(row.get("n_ac")),
            n_dc=_int(row.get("n_dc")),
            n_plugs=_int(row.get("n_plugs")),
            max_capacity_kw=_float(row.get("max_capacity_kw")),
            price_min_php_kwh=_float(row.get("price_min_php_kwh")),
            price_max_php_kwh=_float(row.get("price_max_php_kwh")),
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
        dc_within, max_kw = None, None
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
        has_detail = "n_dc" in near and stations["doe_station_number"].notna().any()
        n_dc = pd.to_numeric(near["n_dc"]) if has_detail else None
        dc_within = None if n_dc is None else int((n_dc.fillna(0) > 0).sum())
        max_kw = _float(pd.to_numeric(near["max_capacity_kw"]).max()) if has_detail else None
    return TransformerEv(
        stations_within=len(near),
        dc_stations_within=dc_within,
        max_capacity_kw_within=max_kw,
        nearest_station_m=nearest,
        radius_m=int(radius_m),
        stations=chargers(near, None),
        adoption_scenario=adoption_scenario(adoption_rows),
    )
