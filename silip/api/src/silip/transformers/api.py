"""Engineer-only routes: the risk map and the transformer card."""

from __future__ import annotations

from functools import lru_cache
from time import monotonic
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from silip.shared.auth.api import AUTH_RESPONSES, Engineer
from silip.shared.config import Settings
from silip.shared.deps import Source
from silip.shared.geo import BoundingBox
from silip.shared.readings.domain import DataSource
from silip.transformers import service
from silip.transformers.domain import (
    TransformerCard,
    TransformerDataUnavailableError,
    TransformerNotFoundError,
    TransformerRisk,
)

router = APIRouter(prefix="/api/v1/transformers", tags=["transformers"])


@lru_cache(maxsize=4)
def _snapshot(
    source: DataSource, forecaster: str, risk_scorer: str, refresh_window: int
) -> service.RiskSnapshot:
    # One scoring run per process and strategy pair; data refreshes on the next cold start.
    return service.compute_risk(source, forecaster, risk_scorer)


def risk_snapshot(source: Source, settings: Settings) -> service.RiskSnapshot:
    return _snapshot(source, settings.forecaster, settings.risk_scorer, int(monotonic() // 60))


Snapshot = Annotated[service.RiskSnapshot, Depends(risk_snapshot)]


@router.get("", response_model=list[TransformerRisk], responses=AUTH_RESPONSES)
def list_transformers(
    snapshot: Snapshot,
    _: Engineer,
    bbox: Annotated[str | None, Query(description="min_lon,min_lat,max_lon,max_lat")] = None,
) -> list[TransformerRisk]:
    """Risk tier, reasons and confidence per transformer, Critical first."""
    try:
        box = BoundingBox.parse(bbox) if bbox else None
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return service.risk_map(snapshot, box)


@router.get("/{transformer_id}", response_model=TransformerCard, responses=AUTH_RESPONSES)
def get_transformer(transformer_id: str, snapshot: Snapshot, _: Engineer) -> TransformerCard:
    """One transformer: risk, last 48 h of load and the 24 h forecast."""
    try:
        return service.transformer_card(snapshot, transformer_id)
    except TransformerDataUnavailableError as error:
        raise HTTPException(409, "Not enough readings to forecast this transformer yet") from error
    except TransformerNotFoundError as error:
        raise HTTPException(status_code=404, detail="Transformer not found") from error
