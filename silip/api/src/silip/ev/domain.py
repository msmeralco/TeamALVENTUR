"""EV loader records: station provenance, adoption statistics, exposure rows, and the store port.

The pure station and exposure core lives in `silip_ml.ev` (shared with the risk features)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

import pandas as pd

STATION_SOURCE = "DOE EVCS list (data/evcs_locations.csv)"
STATION_COLUMNS = [
    "station_id",
    "name",
    "region",
    "province",
    "city",
    "barangay",
    "lat",
    "lon",
    "source",
    "source_sha256",
    "loaded_at",
    "is_simulated",
]
ADOPTION_KEY = ["period", "geography_level", "geography", "metric", "vehicle_class"]
ADOPTION_COLUMNS = [
    *ADOPTION_KEY,
    "value",
    "unit",
    "source_url",
    "retrieved_at",
    "is_simulated",
]
ADOPTION_METRICS = frozenset({"ev_sales", "ev_registrations", "ev_stock", "ev_share_of_sales"})
EXPOSURE_COLUMNS = [
    "transformer_id",
    "radius_m",
    "stations_within",
    "nearest_station_m",
    "source_sha256",
    "computed_at",
    "is_simulated",
]

AdoptionStatus = Literal["loaded", "not_loaded"]


@dataclass(frozen=True)
class EvLoad:
    """One loader pass: cleaned stations, adoption rows (empty if not delivered), exposure."""

    stations: pd.DataFrame
    adoption: pd.DataFrame
    exposure: pd.DataFrame
    rows_read: int
    dropped_outside_ph: int
    duplicates: int
    source_sha256: str
    adoption_status: AdoptionStatus
    loaded_at: datetime


class EvStore(Protocol):
    """Where a loader pass goes (Neon) or is kept (in memory, for DATA_SOURCE=simulated)."""

    def write(self, load: EvLoad) -> None: ...

    def stations(self) -> pd.DataFrame: ...

    def adoption(self) -> pd.DataFrame: ...

    def exposure(self) -> pd.DataFrame: ...
