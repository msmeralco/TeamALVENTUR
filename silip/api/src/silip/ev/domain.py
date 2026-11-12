"""EV loader records: station provenance, adoption statistics, exposure rows, and the store port.

The pure station and exposure core lives in `silip_ml.ev` (shared with the risk features)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

import pandas as pd
from pydantic import BaseModel

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
ScenarioLabel = Literal["Scenario, not a forecast"]


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


class Charger(BaseModel):
    """One public DOE charging station (a public site, not a home)."""

    station_id: str
    name: str
    lat: float
    lon: float
    barangay: str | None
    city: str | None


class ChargerMap(BaseModel):
    """DOE stations in view, and the radius used to link them to transformers."""

    radius_m: int
    source: str
    stations: list[Charger]
    is_simulated: bool


class AdoptionPoint(BaseModel):
    period: str
    geography_level: str
    geography: str
    metric: str
    vehicle_class: str
    value: float
    unit: str


class Adoption(BaseModel):
    """Delivered EV adoption statistics; `not_loaded` until the file arrives."""

    status: AdoptionStatus
    series: list[AdoptionPoint]
    source_url: str | None
    is_simulated: bool


class AdoptionScenario(BaseModel):
    """The latest adoption figure, shown for planning only. Not a model input."""

    label: ScenarioLabel = "Scenario, not a forecast"
    period: str
    geography: str
    metric: str
    vehicle_class: str
    value: float
    unit: str
    source_url: str | None


class TransformerEv(BaseModel):
    """EV exposure of one transformer: DOE stations within the radius."""

    stations_within: int
    nearest_station_m: float | None
    radius_m: int
    stations: list[Charger]
    adoption_scenario: AdoptionScenario | None
