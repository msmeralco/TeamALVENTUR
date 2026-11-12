"""Forecast and score every transformer with the configured strategies."""

from __future__ import annotations

from collections.abc import Hashable, Mapping
from dataclasses import dataclass
from typing import Any

import pandas as pd

from silip.shared.geo import BoundingBox
from silip.shared.readings.domain import DataSource
from silip.transformers.domain import (
    LoadPoint,
    TransformerCard,
    TransformerNotFoundError,
    TransformerRisk,
)
from silip_ml.core.registry import create
from silip_ml.readings.domain import STEPS_PER_DAY, load_pct
from silip_ml.risk.domain import RiskOutput

CARD_HISTORY = pd.Timedelta(hours=48)


@dataclass(frozen=True)
class RiskSnapshot:
    """One scoring run: risk per transformer plus the forecast behind it."""

    transformers: pd.DataFrame
    load: pd.DataFrame
    forecast: pd.DataFrame
    risk: dict[str, RiskOutput]


def compute_risk(source: DataSource, forecaster: str, risk_scorer: str) -> RiskSnapshot:
    """Forecast the next 24 h and score it. Strategies are chosen by name (config)."""
    transformers, load = source.transformers(), source.load()
    forecast = create("forecaster", forecaster).fit(load).predict(load, STEPS_PER_DAY)
    outputs = (
        create("risk_scorer", risk_scorer).fit(load, transformers).score(forecast, transformers)
    )
    return RiskSnapshot(transformers, load, forecast, {o.transformer_id: o for o in outputs})


def _risk_row(snapshot: RiskSnapshot, row: Mapping[Hashable, Any]) -> TransformerRisk:
    return TransformerRisk(
        transformer_id=row["transformer_id"],
        lat=row["lat"],
        lon=row["lon"],
        rated_kva=row["rated_kva"],
        risk=snapshot.risk[row["transformer_id"]],
        is_simulated=bool(row["is_simulated"]),
    )


def risk_map(snapshot: RiskSnapshot, bbox: BoundingBox | None) -> list[TransformerRisk]:
    """Every transformer inside `bbox` (all when None), Critical first."""
    order = {"Critical": 0, "Watch": 1, "OK": 2}
    rows = [
        _risk_row(snapshot, row)
        for row in snapshot.transformers.to_dict("records")
        if bbox is None or bbox.contains(row["lat"], row["lon"])
    ]
    return sorted(rows, key=lambda r: (order[r.risk.tier], -r.risk.peak_load_pct))


def transformer_card(snapshot: RiskSnapshot, transformer_id: str) -> TransformerCard:
    """Risk plus recent and forecast load for one transformer."""
    match = snapshot.transformers[snapshot.transformers["transformer_id"] == transformer_id]
    if match.empty:
        raise TransformerNotFoundError(transformer_id)
    row = match.to_dict("records")[0]
    history = snapshot.load[snapshot.load["transformer_id"] == transformer_id]
    as_of = history["ts"].max()
    history = history[history["ts"] > as_of - CARD_HISTORY]
    forecast = snapshot.forecast[snapshot.forecast["transformer_id"] == transformer_id]
    points = [
        LoadPoint(
            ts=ts, kw=kw, load_pct=float(load_pct(kw, row["rated_kva"])), is_forecast=is_forecast
        )
        for frame, column, is_forecast in (
            (history, "transformer_kw", False),
            (forecast, "kw_pred", True),
        )
        for ts, kw in zip(frame["ts"], frame[column], strict=True)
    ]
    return TransformerCard(**_risk_row(snapshot, row).model_dump(), as_of=as_of, load=points)
