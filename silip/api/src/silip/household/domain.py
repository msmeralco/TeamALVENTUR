"""Household usage response shape."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from silip_ml.readings.domain import Motion

HOURS_PER_INTERVAL = 0.25


class HouseholdNotLinkedError(LookupError):
    """The signed-in account has no household linked to it."""


class UsagePoint(BaseModel):
    ts: datetime
    kw: float


class HouseholdUsage(BaseModel):
    """The last 7 days of the household's own load, in 15-minute intervals."""

    total_kwh: float
    points: list[UsagePoint]
    is_simulated: bool


class ElectricalReading(BaseModel):
    ts: datetime
    voltage_v: float
    current_a: float
    power_kw: float
    power_factor: float
    energy_kwh_interval: float
    motion: Motion | None
    event: str | None
    is_simulated: bool


class HouseholdDevice(BaseModel):
    clamp_id: str
    transformer_id: str
    lat: float | None
    lon: float | None
    location_label: str | None = None
    ct_model: str
    last_seen_at: datetime | None
    is_simulated: bool
    readings: list[ElectricalReading]
