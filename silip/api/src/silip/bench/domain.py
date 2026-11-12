"""Response shapes for the public /demo page. Bench rig only: mock households, never real ones."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from silip.shared.bench.domain import Tier

Mode = Literal["live", "replay"]


class NotBenchError(LookupError):
    """The transformer is not part of the bench rig, so these public routes will not serve it."""


class BenchHomeState(BaseModel):
    label: str
    watts: float | None  # None until the home's first reading in the window
    volts: float | None
    powered: bool
    updated_at: datetime | None


class BenchTransformerState(BaseModel):
    transformer_id: str
    rated_w: float
    total_w: float
    load_pct: float
    tier: Tier
    reasons: list[str]
    homes_reporting: int  # homes summed by SIN for total_w
    homes_on_record: int
    homes: list[BenchHomeState]  # the homes the records list under this transformer
    powered: bool


class BenchFingerprint(BaseModel):
    home: str
    record_transformer: str
    voltage_transformer: str | None
    confidence: float
    mismatch: bool
    explanation: str


class BenchSnapshot(BaseModel):
    as_of: datetime
    mode: Mode | None  # None when no readings in the window
    is_simulated: bool
    sample_interval_s: float
    transformers: list[BenchTransformerState]
    fingerprints: list[BenchFingerprint]
