"""Response shapes for the clamp layer of the engineer map. Device facts only, never usage."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ClampStatus = Literal["online", "offline"]


class ClampPoint(BaseModel):
    """One installed clamp, placed at its household's building. Carries no household identity."""

    clamp_id: str
    transformer_id: str
    lat: float
    lon: float
    ct_model: str
    installed_at: datetime
    last_seen_at: datetime | None
    status: ClampStatus
    is_simulated: bool


class ClampMap(BaseModel):
    """Every clamp in view, with status judged against `as_of` (the latest report of any clamp)."""

    as_of: datetime | None
    offline_after_min: int
    clamps: list[ClampPoint]
    is_simulated: bool
