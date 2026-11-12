"""Engineer-only routes: the risk map and the transformer card."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from silip.ev.api import Ev
from silip.shared.auth.api import AUTH_RESPONSES, Engineer
from silip.shared.config import Settings
from silip.shared.deps import Source, Store
from silip.shared.geo import BoundingBox, parse_bbox
from silip.shared.readings.domain import DataSource
from silip.transformers import service
from silip.transformers.domain import (
    TransformerCard,
    TransformerDataUnavailableError,
    TransformerNotFoundError,
    TransformerRisk,
)
from silip.weather.api import Forecast, Now, Reader

router = APIRouter(prefix="/api/v1/transformers", tags=["transformers"])

# Simulated mode recomputes at most once per reading interval (iot/include/config.h
# PUBLISH_INTERVAL_MS, 15 min), so a fresher answer could not have new data anyway.
SCORE_TTL = pd.Timedelta(minutes=15)
NO_RUN_DETAIL = "No completed scoring run yet"
RESPONSES = {**AUTH_RESPONSES, 503: {"description": NO_RUN_DETAIL}}

_computed: dict[tuple[DataSource, str, str], service.RiskSnapshot] = {}


def utc_now() -> datetime:
    """The request clock; tests override this dependency to expire the cache."""
    return datetime.now(UTC)


def risk_snapshot(
    source: Source,
    store: Store,
    settings: Settings,
    now: Annotated[datetime, Depends(utc_now)],
    reader: Reader,
    ev: Ev,
) -> service.RiskSnapshot:
    if store is not None:
        stored = store.latest_run()
        if stored is None:
            raise HTTPException(status_code=503, detail=NO_RUN_DETAIL)
        return service.snapshot_from_run(stored, source.transformers())
    key = (source, settings.forecaster, settings.risk_scorer)
    cached = _computed.get(key)
    if cached is None or now - cached.scored_at >= SCORE_TTL:
        try:
            cached = _computed[key] = service.compute_risk(
                source, *key[1:], now, reader, ev.exposure()
            )
        except service.NoLoadDataError as error:
            raise HTTPException(status_code=503, detail="No load data yet") from error
    return cached


Snapshot = Annotated[service.RiskSnapshot, Depends(risk_snapshot)]
Bbox = Annotated[BoundingBox | None, Depends(parse_bbox)]


@router.get("", response_model=list[TransformerRisk], responses=RESPONSES)
def list_transformers(
    _: Engineer, snapshot: Snapshot, source: Source, ev: Ev, box: Bbox
) -> list[TransformerRisk]:
    """Risk tier, action, peak time, top reason, heat, EV and clamp health per transformer,
    Critical first."""
    return service.risk_map(snapshot, source, box, ev.exposure())


@router.get("/{transformer_id}", response_model=TransformerCard, responses=RESPONSES)
def get_transformer(
    transformer_id: str,
    _: Engineer,
    snapshot: Snapshot,
    source: Source,
    forecast: Forecast,
    weather_now: Now,
    ev: Ev,
    settings: Settings,
) -> TransformerCard:
    """One transformer: risk, drivers, last 48 h of load and the 24 h forecast, the next 48 h of
    weather, EV exposure and clamp health."""
    try:
        return service.transformer_card(
            snapshot,
            source,
            transformer_id,
            forecast,
            weather_now,
            ev.stations(),
            ev.adoption(),
            live_weather=settings.weather_source == "open_meteo",
        )
    except TransformerDataUnavailableError as error:
        raise HTTPException(409, "Not enough readings to forecast this transformer yet") from error
    except TransformerNotFoundError as error:
        raise HTTPException(status_code=404, detail="Transformer not found") from error
