"""Response shapes for the risk map and transformer card."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from silip.ev.domain import TransformerEv
from silip.shared.scores.domain import Action, ClampHealth, Driver
from silip.weather.domain import WeatherHour
from silip_ml.risk.domain import RiskOutput


class TransformerNotFoundError(LookupError):
    """No transformer with that ID."""


class TransformerDataUnavailableError(LookupError):
    """The transformer does not have enough readings for a reliable forecast yet."""


class TransformerRisk(BaseModel):
    """One pin on the engineer risk map, and one row of the action queue.

    Dashboard fields are null on runs scored before they existed.
    """

    transformer_id: str
    lat: float
    lon: float
    rated_kva: float
    risk: RiskOutput
    is_simulated: bool
    scored_at: datetime | None = None
    action: Action | None = None
    peak_ts: datetime | None = None
    top_reason: str | None = None
    heat_index_max_c: float | None = Field(
        default=None, description="Highest forecast heat index in the next 24 h, °C"
    )
    ev_stations_within: int | None = Field(
        default=None, description="Public DOE chargers within the EV radius"
    )
    ev_evening_step_kw: float | None = Field(
        default=None, description="Evening load step: last 7 days minus days 8 to 28, kW"
    )
    clamp_health: ClampHealth | None = None
    open_outage: bool = False


class LoadPoint(BaseModel):
    """Transformer load at one 15-minute interval; `is_forecast` marks the predicted part."""

    ts: datetime
    kw: float
    load_pct: float
    is_forecast: bool


class TransformerCard(TransformerRisk):
    """The transformer card: risk plus the last 48 h and the next 24 h of load, why it is
    flagged, the weather ahead, EV exposure and how many more clamps would reach the target."""

    as_of: datetime
    load: list[LoadPoint]
    drivers: list[Driver] = Field(default_factory=list)
    weather: list[WeatherHour] = Field(default_factory=list)
    weather_note: str | None = Field(
        default=None, description="Set when a live forecast sits beside simulated load data"
    )
    ev: TransformerEv
    clamps_to_target: int | None = None
