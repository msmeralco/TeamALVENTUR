"""Household usage response shape."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

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
