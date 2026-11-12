"""Response shapes for the risk map and transformer card."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from silip_ml.risk.domain import RiskOutput


class TransformerNotFoundError(LookupError):
    """No transformer with that ID."""


class TransformerRisk(BaseModel):
    """One pin on the engineer risk map."""

    transformer_id: str
    lat: float
    lon: float
    rated_kva: float
    risk: RiskOutput
    is_simulated: bool


class LoadPoint(BaseModel):
    """Transformer load at one 15-minute interval; `is_forecast` marks the predicted part."""

    ts: datetime
    kw: float
    load_pct: float
    is_forecast: bool


class TransformerCard(TransformerRisk):
    """The transformer card: risk plus the last 48 h and the next 24 h of load."""

    as_of: datetime
    load: list[LoadPoint]
