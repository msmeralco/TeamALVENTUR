"""DOE EV charging stations: normalise the delivered list and join stations to transformers.

Pure functions shared by the API loader (`silip.ev`) and the risk features. No I/O here.
"""

from __future__ import annotations

import hashlib
import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

EV_STATION_RADIUS_M = 1000  # [VERIFY] distance at which a public charger plausibly shares a feeder
# Philippines with a small margin: drops swapped or zero coordinates. [VERIFY] against PSA bounds.
PH_MIN_LAT, PH_MAX_LAT = 4.5, 21.2
PH_MIN_LON, PH_MAX_LON = 116.9, 126.7
EARTH_RADIUS_M = 6_371_000.0

# data/evcs_locations.csv header (as delivered) -> snake_case station columns.
STATION_HEADER = {
    "EVCS Establishment": "name",
    "Region": "region",
    "Province": "province",
    "City/Municipality": "city",
    "Barangay": "barangay",
    "Latitude": "lat",
    "Longitude": "lon",
}
STATION_FIELDS = ["station_id", "name", "region", "province", "city", "barangay", "lat", "lon"]

# DOE station detail and plug files (from the DOE EVCS portal). Only these columns are ever read:
# contact_no, email_website, street_view_url, equipment_serial, n_photos, payment_method,
# restrictions and status_reason (free text) are never loaded.
DETAIL_COLUMNS = [
    "station_number", "name", "latitude", "longitude", "address", "classification",
    "n_chargepoints", "n_ac", "n_dc", "n_plugs", "price_min_php_kwh", "price_max_php_kwh", "hours",
]  # fmt: skip
DETAIL_FIELDS = [
    "station_id", "doe_station_number", "address", "classification", "n_chargepoints", "n_ac",
    "n_dc", "n_plugs", "max_capacity_kw", "price_min_php_kwh", "price_max_php_kwh", "hours",
]  # fmt: skip
PLUG_COLUMNS = [
    "station_number", "plug_id", "mode", "chargepoint_status", "protocol", "charging_capacity",
    "price_php", "pricing_strategy",
]  # fmt: skip
PLUG_FIELDS = [
    "station_id",
    "plug_id",
    "mode",
    "protocol",
    "capacity_kw",
    "status",
    "price_php_kwh",
]
PER_KWH_PRICING = "Variable/Consumption Fees (Php/kWh)"  # other strategies are PHP, not PHP/kWh


def station_id(name: str, lat: float, lon: float) -> str:
    """First 16 hex of sha256("name|lat|lon"): stable across reloads of the same station."""
    return hashlib.sha256(f"{name}|{lat}|{lon}".encode()).hexdigest()[:16]


def normalise_stations(raw: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    """Delivered rows -> STATION_FIELDS inside the Philippines, one row per station_id.

    Returns (stations, dropped_outside_ph, duplicates). Rows without a name count as dropped.

    Raises:
        ValueError: if the delivered header lacks a required column.
    """
    missing = set(STATION_HEADER) - set(raw.columns)
    if missing:
        raise ValueError(f"evcs_locations.csv is missing columns: {sorted(missing)}")
    frame = raw[list(STATION_HEADER)].rename(columns=STATION_HEADER)
    for column in ("name", "region", "province", "city", "barangay"):
        frame[column] = frame[column].astype("string").str.strip()
    frame["lat"] = pd.to_numeric(frame["lat"], errors="coerce")
    frame["lon"] = pd.to_numeric(frame["lon"], errors="coerce")
    inside = frame["lat"].between(PH_MIN_LAT, PH_MAX_LAT) & frame["lon"].between(
        PH_MIN_LON, PH_MAX_LON
    )
    inside &= frame["name"].notna() & (frame["name"] != "")
    dropped = int((~inside).sum())
    if dropped:
        logger.info("dropped %d station rows outside the Philippines or without a name", dropped)
    frame = frame[inside].copy()
    frame["station_id"] = [
        station_id(name, lat, lon)
        for name, lat, lon in zip(frame["name"], frame["lat"], frame["lon"], strict=True)
    ]
    before = len(frame)
    frame = frame.drop_duplicates("station_id").reset_index(drop=True)
    return frame[STATION_FIELDS].copy(), dropped, before - len(frame)


def _numbers(column: pd.Series) -> pd.Series:
    return pd.to_numeric(column.replace("", np.nan), errors="coerce")


def _text(column: pd.Series) -> pd.Series:
    text = column.astype("string").str.strip()
    return text.mask(text == "")


def normalise_details(
    detail: pd.DataFrame, plugs: pd.DataFrame | None, station_ids: pd.Series
) -> tuple[pd.DataFrame, pd.DataFrame, int, int]:
    """Detail and plug rows -> DETAIL_FIELDS and PLUG_FIELDS for stations in `station_ids`.

    A detail row joins its station on station_id(name without commas, lat, lon): the delivered
    locations file spells names without commas. Capacity is kW ([VERIFY] the portal's unit;
    delivered values are 6 to 120, AC 7/22, DC 40 to 120). A plug's price is kept only when it is
    per kWh. `plug_id` is the DOE label plus its occurrence within the station (labels repeat
    across chargepoints). Returns (details, plugs, unmatched_details, plugs_without_station).

    Raises:
        ValueError: if either file lacks a required column.
    """
    missing = set(DETAIL_COLUMNS) - set(detail.columns)
    if missing:
        raise ValueError(f"evcs_stations_detail.csv is missing columns: {sorted(missing)}")
    frame = detail[DETAIL_COLUMNS].copy()
    lat, lon = _numbers(frame["latitude"]), _numbers(frame["longitude"])
    frame["station_id"] = [
        station_id(str(name).replace(",", "").strip(), a, b)
        for name, a, b in zip(frame["name"], lat, lon, strict=True)
    ]
    matched = frame["station_id"].isin(set(station_ids))
    frame = frame[matched].drop_duplicates("station_id").copy()
    frame["doe_station_number"] = frame["station_number"].astype(str).str.strip()
    for column in ("n_chargepoints", "n_ac", "n_dc", "n_plugs"):
        frame[column] = _numbers(frame[column]).astype("Int64")
    for column in ("price_min_php_kwh", "price_max_php_kwh"):
        frame[column] = _numbers(frame[column])
    for column in ("address", "classification", "hours"):
        frame[column] = _text(frame[column])

    plug_frame = pd.DataFrame(columns=PLUG_FIELDS)
    orphans = 0
    frame["max_capacity_kw"] = np.nan
    if plugs is not None:
        missing = set(PLUG_COLUMNS) - set(plugs.columns)
        if missing:
            raise ValueError(f"evcs_plugs.csv is missing columns: {sorted(missing)}")
        raw = plugs[PLUG_COLUMNS].copy()
        ids = frame.set_index("doe_station_number")["station_id"]
        raw["station_id"] = raw["station_number"].astype(str).str.strip().map(ids)
        orphans = int(raw["station_id"].isna().sum())
        raw = raw[raw["station_id"].notna()].copy()
        label = raw["plug_id"].astype(str).str.strip()
        occurrence = raw.assign(label=label).groupby(["station_id", "label"]).cumcount() + 1
        raw["plug_id"] = label + " #" + occurrence.astype(str)
        raw["capacity_kw"] = _numbers(raw["charging_capacity"])
        raw["status"] = (
            raw["chargepoint_status"].astype(str).map({"1": "operational", "0": "out_of_service"})
        )
        per_kwh = raw["pricing_strategy"] == PER_KWH_PRICING
        raw["price_php_kwh"] = _numbers(raw["price_php"]).where(per_kwh)
        for column in ("mode", "protocol"):
            raw[column] = _text(raw[column])
        plug_frame = raw[PLUG_FIELDS].reset_index(drop=True)
        best = plug_frame.groupby("station_id")["capacity_kw"].max()
        frame["max_capacity_kw"] = frame["station_id"].map(best).astype(float)
    return frame[DETAIL_FIELDS].reset_index(drop=True), plug_frame, int((~matched).sum()), orphans


def haversine_m(
    lat_a: np.ndarray, lon_a: np.ndarray, lat_b: np.ndarray, lon_b: np.ndarray
) -> np.ndarray:
    """Great-circle distances in metres, shape (len(a), len(b))."""
    phi_a, phi_b = np.radians(lat_a)[:, None], np.radians(lat_b)[None, :]
    d_phi = phi_b - phi_a
    d_lambda = np.radians(lon_b)[None, :] - np.radians(lon_a)[:, None]
    h = np.sin(d_phi / 2) ** 2 + np.cos(phi_a) * np.cos(phi_b) * np.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(np.clip(h, 0.0, 1.0)))


def exposure(
    transformers: pd.DataFrame, stations: pd.DataFrame, radius_m: float = EV_STATION_RADIUS_M
) -> pd.DataFrame:
    """Per transformer: stations within `radius_m` and the nearest station's distance (haversine).

    `transformers` needs transformer_id, lat, lon; `stations` needs lat, lon. One vectorized
    transformers x stations distance matrix; `nearest_station_m` is NaN when there are no stations.
    With the DOE detail on `stations` (`n_dc`, `max_capacity_kw`), also the DC stations within the
    radius and the largest known plug capacity there (NaN when none is known, or without detail).
    """
    distances = haversine_m(
        transformers["lat"].to_numpy(float),
        transformers["lon"].to_numpy(float),
        stations["lat"].to_numpy(float),
        stations["lon"].to_numpy(float),
    )
    has_stations = distances.shape[1] > 0
    near = distances <= radius_m
    dc_within: np.ndarray | float = np.nan
    max_kw: np.ndarray | float = np.nan
    if "n_dc" in stations and "max_capacity_kw" in stations:
        is_dc = pd.to_numeric(stations["n_dc"]).fillna(0).to_numpy(float) > 0
        dc_within = (near & is_dc[None, :]).sum(axis=1)
        capacity = pd.to_numeric(stations["max_capacity_kw"]).to_numpy(float)
        known = near & ~np.isnan(capacity)[None, :]
        best = np.where(known, capacity[None, :], -np.inf).max(axis=1, initial=-np.inf)
        max_kw = np.where(np.isinf(best), np.nan, best)
    return pd.DataFrame(
        {
            "transformer_id": transformers["transformer_id"].to_numpy(),
            "radius_m": int(radius_m),
            "stations_within": near.sum(axis=1).astype(int),
            "nearest_station_m": distances.min(axis=1) if has_stations else np.nan,
            "dc_stations_within": dc_within,
            "max_capacity_kw_within": max_kw,
        }
    )
