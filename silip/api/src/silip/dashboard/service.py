"""Dashboard fields for every scored transformer: peak time, drivers, heat, EV step, clamp
health and the recommended action. Used by the scoring job and by the simulated-mode API."""

from __future__ import annotations

from collections.abc import Hashable, Mapping
from dataclasses import dataclass
from typing import Any

import pandas as pd

from silip.dashboard.domain import (
    HISTORY_WINDOW,
    by_transformer,
    clamp_health,
    driver,
    elevated_days,
    evening_step_kw,
    heat_peak,
    offline_share,
    open_outage_ids,
    recommend_action,
    rule_drivers,
)
from silip.shared.readings.domain import DataSource
from silip.shared.scores.domain import Driver, Scored, ScoreDetail
from silip.shared.scores.service import score_window
from silip.weather.domain import SOURCE_LABELS, WeatherOutlook
from silip_ml.risk.domain import RiskOutput
from silip_ml.weather import cell_id

RISK_HORIZON = pd.Timedelta(hours=24)
# Weather-aware forecaster -> the one used when no usable forecast exists (ADR 0006).
NON_WEATHER_FORECASTER = {"lightgbm_weather": "lightgbm"}


@dataclass(frozen=True)
class Assessed:
    """One scoring pass with its dashboard fields. `forecaster` is the one actually used."""

    scores: tuple[RiskOutput, ...]
    forecast: pd.DataFrame
    details: tuple[ScoreDetail, ...]
    forecaster: str


def model_drivers(
    score: RiskOutput, row: Mapping[Hashable, Any] | None, weather_source: str
) -> list[Driver]:
    """Per-feature drivers from the risk model (`RiskOutput.drivers`: feature, contribution and
    sentence), when it gives them; empty for the rules scorer."""
    return [
        driver(
            str(item.feature),
            str(getattr(item, "text", None) or item.feature),
            row,
            getattr(item, "contribution", None),
            weather_source,
        )
        for item in getattr(score, "drivers", None) or []
    ]


def score_details(
    scored: Scored,
    source: DataSource,
    as_of: pd.Timestamp,
    weather: pd.DataFrame,
    weather_source: str,
) -> tuple[ScoreDetail, ...]:
    """One ScoreDetail per score in `scored`. `weather` is the forecast used (may be empty);
    `weather_source` labels weather drivers ("Simulated" or "Open-Meteo")."""
    transformers = source.transformers()
    info = by_transformer(transformers)
    counts = by_transformer(source.clamp_counts(as_of.to_pydatetime()))
    outages = open_outage_ids(source.outages(), as_of)
    steps = evening_step_kw(scored.history, as_of)
    days = elevated_days(scored.history, transformers, as_of)
    features = by_transformer(scored.features) if not scored.features.empty else {}
    details = []
    for score in scored.scores:
        tid = score.transformer_id
        row = info[tid]
        found = counts.get(tid, {})
        health = clamp_health(
            int(row["homes"]),
            int(found.get("clamps_installed", 0)),
            int(found.get("clamps_online", 0)),
        )
        feature_row = features.get(tid)
        drivers = model_drivers(score, feature_row, weather_source)
        if not drivers and feature_row is not None:
            drivers = rule_drivers(feature_row, score.reasons)
        peak_ts = getattr(score, "peak_ts", None)
        if peak_ts is None and feature_row is not None:
            peak_ts = pd.Timestamp(feature_row["peak_ts"]).to_pydatetime()
        heat = heat_peak(
            weather, cell_id(float(row["lat"]), float(row["lon"])), as_of, as_of + RISK_HORIZON
        )
        step = steps.get(tid)
        details.append(
            ScoreDetail(
                transformer_id=tid,
                peak_ts=peak_ts,
                action=recommend_action(
                    score.tier,
                    health.reporting_pct,
                    offline_share(health),
                    tid in outages,
                    days.get(tid, 0),
                    step,
                ),
                drivers=drivers,
                heat_index_max_c=None if heat is None else round(heat[0], 1),
                ev_evening_step_kw=None if step is None else round(step, 2),
                homes_reporting=health.homes_reporting,
                clamps_installed=health.clamps_installed,
                clamps_online=health.clamps_online,
            )
        )
    return tuple(details)


def assess(
    source: DataSource,
    as_of: pd.Timestamp,
    forecaster: str,
    risk_scorer: str,
    weather: WeatherOutlook,
    ev_exposure: pd.DataFrame | None,
) -> Assessed:
    """Forecast, score and decide for every transformer at `as_of`.

    Without a usable forecast (status missing) a weather-aware forecaster falls back to its
    non-weather twin. A score is simulated if any input, the weather included, is.
    """
    if weather.status == "missing":
        forecaster = NON_WEATHER_FORECASTER.get(forecaster, forecaster)
    scored = score_window(
        source,
        as_of.to_pydatetime(),
        forecaster,
        risk_scorer,
        weather=weather.rows,
        ev_exposure=ev_exposure,
        history_window=HISTORY_WINDOW,
    )
    scores, forecast = scored.scores, scored.forecast
    if weather.is_simulated:
        scores = tuple(score.model_copy(update={"is_simulated": True}) for score in scores)
        forecast = forecast.assign(is_simulated=True)
    label = SOURCE_LABELS["simulated" if weather.is_simulated else "open_meteo"]
    details = score_details(scored, source, as_of, weather.rows, label)
    return Assessed(scores, forecast, details, forecaster)
