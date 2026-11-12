"""Risk map and transformer card from one scoring run (stored, or computed on request)."""

from __future__ import annotations

from collections.abc import Hashable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from silip.dashboard.domain import clamp_health, clamps_to_target, open_outage_ids
from silip.dashboard.service import assess
from silip.ev.service import transformer_ev
from silip.shared.geo import BoundingBox
from silip.shared.readings.adapters import LOCAL_TZ
from silip.shared.readings.domain import DataSource
from silip.shared.scores.domain import ScoreDetail, StoredRun, WeatherStatus
from silip.transformers.domain import (
    LoadPoint,
    TransformerCard,
    TransformerDataUnavailableError,
    TransformerNotFoundError,
    TransformerRisk,
)
from silip.weather.domain import LIVE_ON_SIMULATED_NOTE, WeatherOutlook, WeatherReader
from silip.weather.service import cell_hours, no_forecast, outlook
from silip_ml.readings.domain import load_pct
from silip_ml.risk.domain import RiskOutput
from silip_ml.weather import cell_id

CARD_HISTORY = pd.Timedelta(hours=48)
TIER_ORDER = {"Critical": 0, "Watch": 1, "OK": 2}


class NoLoadDataError(LookupError):
    """The source has no load rows yet, so there is nothing to score."""


@dataclass(frozen=True)
class RiskSnapshot:
    """One scoring run: risk per transformer, the forecast behind it and its dashboard fields."""

    transformers: pd.DataFrame
    forecast: pd.DataFrame
    risk: dict[str, RiskOutput]
    as_of: pd.Timestamp  # latest load interval scored
    scored_at: datetime
    details: dict[str, ScoreDetail] = field(default_factory=dict)
    forecaster: str | None = None
    risk_scorer: str | None = None
    weather_issued_at: datetime | None = None
    weather_status: WeatherStatus | None = None


def compute_risk(
    source: DataSource,
    forecaster: str,
    risk_scorer: str,
    now: datetime,
    weather_reader: WeatherReader | None = None,
    ev_exposure: pd.DataFrame | None = None,
) -> RiskSnapshot:
    """Score on request (DATA_SOURCE=simulated, no score store). Strategies are chosen by name.

    Simulated forecasts are read on the data's own clock, as the scoring job does.
    """
    as_of = source.latest_load_ts()
    if as_of is None:
        raise NoLoadDataError
    weather = (
        no_forecast() if weather_reader is None else outlook(weather_reader, as_of.to_pydatetime())
    )
    assessed = assess(source, as_of, forecaster, risk_scorer, weather, ev_exposure)
    return RiskSnapshot(
        source.transformers(),
        assessed.forecast,
        {score.transformer_id: score for score in assessed.scores},
        as_of,
        now,
        {detail.transformer_id: detail for detail in assessed.details},
        assessed.forecaster,
        risk_scorer,
        weather.issued_at,
        weather.status,
    )


def snapshot_from_run(stored: StoredRun, transformers: pd.DataFrame) -> RiskSnapshot:
    """The stored run's scores, on transformers that run scored (newer ones wait for the next)."""
    risk = {score.transformer_id: score for score in stored.scores}
    scored = transformers[transformers["transformer_id"].isin(list(risk))]
    as_of = pd.Timestamp(stored.run.as_of).tz_convert(LOCAL_TZ)
    return RiskSnapshot(
        scored,
        stored.forecast,
        risk,
        as_of,
        stored.run.finished_at,
        {detail.transformer_id: detail for detail in stored.details},
        stored.run.forecaster,
        stored.run.risk_scorer,
        stored.run.weather_issued_at,
        stored.run.weather_status,
    )


def _stations_within(exposure: pd.DataFrame | None) -> dict[str, int]:
    if exposure is None or exposure.empty:
        return {}
    return {
        str(k): int(v)
        for k, v in zip(exposure["transformer_id"], exposure["stations_within"], strict=True)
    }


def _risk_row(
    snapshot: RiskSnapshot,
    row: Mapping[Hashable, Any],
    stations_within: Mapping[str, int],
    open_outages: set[str],
) -> TransformerRisk:
    tid = row["transformer_id"]
    risk = snapshot.risk[tid]
    detail = snapshot.details.get(tid)
    health = None
    if detail is not None and detail.clamps_installed is not None:
        health = clamp_health(int(row["homes"]), detail.clamps_installed, detail.clamps_online or 0)
    return TransformerRisk(
        transformer_id=tid,
        lat=row["lat"],
        lon=row["lon"],
        rated_kva=row["rated_kva"],
        risk=risk,
        is_simulated=bool(row["is_simulated"]) or risk.is_simulated,
        scored_at=snapshot.scored_at,
        action=None if detail is None else detail.action,
        peak_ts=None if detail is None else detail.peak_ts,
        top_reason=risk.reasons[0] if risk.reasons else None,
        heat_index_max_c=None if detail is None else detail.heat_index_max_c,
        ev_stations_within=stations_within.get(tid),
        ev_evening_step_kw=None if detail is None else detail.ev_evening_step_kw,
        clamp_health=health,
        open_outage=tid in open_outages,
    )


def risk_map(
    snapshot: RiskSnapshot,
    source: DataSource,
    bbox: BoundingBox | None,
    ev_exposure: pd.DataFrame | None = None,
) -> list[TransformerRisk]:
    """Every transformer inside `bbox` (all when None), Critical first."""
    stations = _stations_within(ev_exposure)
    outages = open_outage_ids(source.outages(), snapshot.as_of)
    rows = [
        _risk_row(snapshot, row, stations, outages)
        for row in snapshot.transformers.to_dict("records")
        if row["transformer_id"] in snapshot.risk
        and (bbox is None or bbox.contains(row["lat"], row["lon"]))
    ]
    return sorted(rows, key=lambda r: (TIER_ORDER[r.risk.tier], -r.risk.peak_load_pct))


def transformer_card(
    snapshot: RiskSnapshot,
    source: DataSource,
    transformer_id: str,
    weather: WeatherOutlook | None = None,
    weather_now: datetime | None = None,
    stations: pd.DataFrame | None = None,
    adoption: pd.DataFrame | None = None,
    live_weather: bool = False,
) -> TransformerCard:
    """Risk plus the 48 h of load up to the run's interval and the forecast after it, the
    drivers, the next 48 h of weather in its cell, EV exposure and the clamp target.

    `live_weather` (Open-Meteo): `weather` and `heat_index_max_c` come from the live forecast
    after `weather_now`, not from the scoring run, and simulated load gets a note saying so."""
    match = snapshot.transformers[snapshot.transformers["transformer_id"] == transformer_id]
    if match.empty:
        raise TransformerNotFoundError(transformer_id)
    if transformer_id not in snapshot.risk:
        raise TransformerDataUnavailableError(transformer_id)
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
    empty = pd.DataFrame(columns=["station_id", "name", "lat", "lon", "barangay", "city"])
    ev = transformer_ev(
        float(row["lat"]),
        float(row["lon"]),
        stations if stations is not None else empty,
        adoption if adoption is not None else pd.DataFrame(),
    )
    outages = open_outage_ids(source.outages(), snapshot.as_of)
    base = _risk_row(snapshot, row, {transformer_id: ev.stations_within}, outages)
    detail = snapshot.details.get(transformer_id)
    hours = (
        []
        if weather is None
        else cell_hours(
            weather,
            cell_id(float(row["lat"]), float(row["lon"])),
            weather_now if weather_now is not None else snapshot.as_of.to_pydatetime(),
        )
    )
    health = base.clamp_health
    fields = base.model_dump()
    note = None
    if live_weather:
        start = weather_now if weather_now is not None else snapshot.as_of.to_pydatetime()
        heat = [
            hour.heat_index_c
            for hour in hours
            if hour.heat_index_c is not None and hour.ts <= start + timedelta(hours=24)
        ]
        fields["heat_index_max_c"] = round(max(heat), 1) if heat else None
        note = LIVE_ON_SIMULATED_NOTE if base.is_simulated else None
    return TransformerCard(
        **fields,
        weather_note=note,
        as_of=snapshot.as_of,
        load=points,
        drivers=[] if detail is None else detail.drivers,
        weather=hours,
        ev=ev,
        clamps_to_target=None
        if health is None
        else clamps_to_target(health.homes, health.clamps_online),
    )
