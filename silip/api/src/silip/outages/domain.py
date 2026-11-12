"""Outage response shapes. The public view is coarse; the engineer view is exact."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Status = Literal["open", "restored"]
# 3 decimal places is about 110 m: enough to say "your street", not which house.
PUBLIC_COORDINATE_DECIMALS = 3


class OutageNotFoundError(LookupError):
    """No outage with that ID."""


class OutageSummary(BaseModel):
    """Public outage card: area, cause and a restoration range."""

    outage_id: str
    status: Status
    cause: str
    started_at: datetime
    area_lat: float
    area_lon: float
    eta_p10_min: float
    eta_p50_min: float
    eta_p90_min: float
    is_simulated: bool


class OutageDetail(OutageSummary):
    """Engineer view: the exact pin, the transformer, and the evidence behind the pin."""

    transformer_id: str
    pin_lat: float
    pin_lon: float
    last_gasp_count: int
    report_count: int
