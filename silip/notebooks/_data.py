"""Paths and table loading shared by the notebooks. No silip_ml import: notebooks stand alone."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "notebooks").is_dir())
DATA_DIR = ROOT / "data" / "sim"
MODELS_DIR = ROOT / "models"
TZ = "Asia/Manila"
# Philippine regular and special holidays, April to June 2026. [VERIFY] against the 2026 proclamation.
HOLIDAYS = ["2026-04-02", "2026-04-03", "2026-04-04", "2026-04-09", "2026-05-01", "2026-06-12"]

FILES = {
    "transformers": "transformers.csv",
    "sin_map": "sin_map.csv",
    "clamps": "clamps.csv",
    "load": "transformer_load_15m.csv",
    "households": "household_load_15m.csv",
    "readings_raw": "readings_raw.csv",
    "weather": "weather_15m.csv",
    "weather_forecast": "weather_forecast_hourly.csv",
    "outages": "outages.csv",
    "signals": "outage_signals.csv",
}
TIME_COLUMNS = {
    "load": ["ts"],
    "households": ["ts"],
    "readings_raw": ["ts", "received_at"],
    "weather": ["ts"],
    "weather_forecast": ["issued_at", "ts"],
    "outages": ["start_ts"],
    "signals": ["ts"],
    "clamps": ["installed_at", "last_seen_at"],
}


def load_tables(data_dir: Path = DATA_DIR) -> dict[str, pd.DataFrame]:
    """Every CSV that `00_generate_mock_data` writes, with times in Manila time."""
    tables = {}
    for name, filename in FILES.items():
        frame = pd.read_csv(data_dir / filename)
        for column in TIME_COLUMNS.get(name, []):
            frame[column] = pd.to_datetime(frame[column], format="ISO8601", utc=True).dt.tz_convert(TZ)
        tables[name] = frame
    return tables


# DOE EV charging stations, delivered by another session (never scraped here). Same cleaning as
# silip_ml.ev.normalise_stations: inside the Philippines, named, one row per name and location.
STATIONS_FILE = ROOT / "data" / "evcs_locations.csv"
STATION_HEADER = {"EVCS Establishment": "name", "Latitude": "lat", "Longitude": "lon"}
PH_LAT, PH_LON = (4.5, 21.2), (116.9, 126.7)  # [VERIFY] against PSA bounds, as in silip_ml.ev


def load_stations(path: Path = STATIONS_FILE) -> pd.DataFrame:
    """DOE stations as `name, lat, lon`; empty if the file has not landed yet."""
    if not path.exists():
        return pd.DataFrame({"name": pd.Series(dtype="string"), "lat": pd.Series(dtype=float), "lon": pd.Series(dtype=float)})
    frame = pd.read_csv(path)[list(STATION_HEADER)].rename(columns=STATION_HEADER)
    frame["name"] = frame["name"].astype("string").str.strip()
    frame["lat"], frame["lon"] = pd.to_numeric(frame["lat"], errors="coerce"), pd.to_numeric(frame["lon"], errors="coerce")
    inside = frame["lat"].between(*PH_LAT) & frame["lon"].between(*PH_LON) & frame["name"].notna() & (frame["name"] != "")
    return frame[inside].drop_duplicates(["name", "lat", "lon"]).reset_index(drop=True)


def holdout_start(load: pd.DataFrame, holdout_days: int = 7) -> pd.Timestamp:
    """First held-out day: the last `holdout_days` days are never used for training or tuning."""
    days = load["ts"].dt.normalize().drop_duplicates().sort_values()
    return days.iloc[-holdout_days]
