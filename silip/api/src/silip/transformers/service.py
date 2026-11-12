"""Risk map and transformer card from one scoring run (stored, or computed on request)."""

from __future__ import annotations

from collections.abc import Hashable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd

from silip.shared.geo import BoundingBox
from silip.shared.readings.adapters import LOCAL_TZ
from silip.shared.readings.domain import DataSource
from silip.shared.scores.domain import StoredRun
from silip.shared.scores.service import score_window
from silip.transformers.domain import (
    LoadPoint,
    TransformerCard,
    TransformerNotFoundError,
    TransformerRisk,
)
from silip_ml.readings.domain import load_pct
from silip_ml.risk.domain import RiskOutput

CARD_HISTORY = pd.Timedelta(hours=48)


class NoLoadDataError(LookupError):
    """The source has no load rows yet, so there is nothing to score."""


@dataclass(frozen=True)
class RiskSnapshot:
    """One scoring run: risk per transformer plus the forecast behind it."""

    transformers: pd.DataFrame
    forecast: pd.DataFrame
    risk: dict[str, RiskOutput]
    as_of: pd.Timestamp  # latest load interval scored
    scored_at: datetime


def compute_risk(
    source: DataSource, forecaster: str, risk_scorer: str, now: datetime
) -> RiskSnapshot:
    """Score on request (DATA_SOURCE=simulated, no score store). Strategies are chosen by name."""
    as_of = source.latest_load_ts()
    if as_of is None:
        raise NoLoadDataError
    scored = score_window(source, as_of.to_pydatetime(), forecaster, risk_scorer)
    risk = {score.transformer_id: score for score in scored.scores}
    return RiskSnapshot(source.transformers(), scored.forecast, risk, as_of, now)


def snapshot_from_run(stored: StoredRun, transformers: pd.DataFrame) -> RiskSnapshot:
    """The stored run's scores, on transformers that run scored (newer ones wait for the next)."""
    risk = {score.transformer_id: score for score in stored.scores}
    scored = transformers[transformers["transformer_id"].isin(list(risk))]
    as_of = pd.Timestamp(stored.run.as_of).tz_convert(LOCAL_TZ)
    return RiskSnapshot(scored, stored.forecast, risk, as_of, stored.run.finished_at)


def _risk_row(snapshot: RiskSnapshot, row: Mapping[Hashable, Any]) -> TransformerRisk:
    risk = snapshot.risk[row["transformer_id"]]
    return TransformerRisk(
        transformer_id=row["transformer_id"],
        lat=row["lat"],
        lon=row["lon"],
        rated_kva=row["rated_kva"],
        risk=risk,
        is_simulated=bool(row["is_simulated"]) or risk.is_simulated,
        scored_at=snapshot.scored_at,
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


def transformer_card(
    snapshot: RiskSnapshot, source: DataSource, transformer_id: str
) -> TransformerCard:
    """Risk plus the 48 h of load up to the run's interval and the forecast after it."""
    match = snapshot.transformers[snapshot.transformers["transformer_id"] == transformer_id]
    if match.empty:
        raise TransformerNotFoundError(transformer_id)
    row = match.to_dict("records")[0]
    recent = source.load(since=snapshot.as_of - CARD_HISTORY)
    history = recent[
        (recent["transformer_id"] == transformer_id) & (recent["ts"] <= snapshot.as_of)
    ]
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
    return TransformerCard(
        **_risk_row(snapshot, row).model_dump(), as_of=snapshot.as_of, load=points
    )
