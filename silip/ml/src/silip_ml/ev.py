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
    """
    distances = haversine_m(
        transformers["lat"].to_numpy(float),
        transformers["lon"].to_numpy(float),
        stations["lat"].to_numpy(float),
        stations["lon"].to_numpy(float),
    )
    has_stations = distances.shape[1] > 0
    return pd.DataFrame(
        {
            "transformer_id": transformers["transformer_id"].to_numpy(),
            "radius_m": int(radius_m),
            "stations_within": (distances <= radius_m).sum(axis=1).astype(int),
            "nearest_station_m": distances.min(axis=1) if has_stations else np.nan,
        }
    )
