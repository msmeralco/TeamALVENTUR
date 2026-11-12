"""Response shapes for the risk map and transformer card, and the bounding-box filter."""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class BoundingBox:
    """`min_lon,min_lat,max_lon,max_lat`, as in the `bbox` query parameter."""

    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    @classmethod
    def parse(cls, text: str) -> BoundingBox:
        """Raises ValueError if `text` is not four comma-separated numbers in order."""
        parts = [float(part) for part in text.split(",")]
        if len(parts) != 4 or parts[0] > parts[2] or parts[1] > parts[3]:
            raise ValueError("bbox must be min_lon,min_lat,max_lon,max_lat")
        return cls(*parts)

    def contains(self, lat: float, lon: float) -> bool:
        return self.min_lat <= lat <= self.max_lat and self.min_lon <= lon <= self.max_lon
