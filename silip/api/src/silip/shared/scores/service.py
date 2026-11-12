"""Forecast and score every transformer once. Used by the batch job and the simulated-mode API."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from datetime import datetime
from typing import Any

import pandas as pd

from silip.shared.readings.domain import DataSource
from silip.shared.scores.domain import SCORING_WINDOW, Scored
from silip_ml import features as ml_features
from silip_ml.core.registry import create
from silip_ml.readings.domain import STEPS_PER_DAY, STEPS_PER_WEEK

FORECAST_COLUMNS = ["transformer_id", "ts", "kw_pred", "is_simulated"]


def accepted(method: Callable[..., Any], positional: int, **optional: Any) -> dict[str, Any]:
    """The optional keyword inputs `method` declares beyond its first `positional` parameters
    (already passed); older strategies take none of them."""
    names = list(inspect.signature(method).parameters)[positional:]
    return {name: value for name, value in optional.items() if name in names}


def _weather_input(weather: pd.DataFrame | None, transformers: pd.DataFrame) -> object | None:
    """Weather in the shape the weather-aware strategies read (silip_ml.features.weather_input)."""
    build = getattr(ml_features, "weather_input", None)
    if weather is None or weather.empty or build is None:
        return None
    return build(weather, transformers)


def score_window(
    source: DataSource,
    as_of: datetime,
    forecaster: str,
    risk_scorer: str,
    weather: pd.DataFrame | None = None,
    ev_exposure: pd.DataFrame | None = None,
    history_window: pd.Timedelta = SCORING_WINDOW,
) -> Scored:
    """Forecast the 24 h after `as_of` from the `SCORING_WINDOW` before it, then score it.

    `weather` (weather_hourly rows issued at or before `as_of`) and `ev_exposure`
    (stations_within per transformer) reach the strategies that declare `weather` or `history`
    inputs. `history_window` (at least SCORING_WINDOW) is how much load `Scored.history` keeps.
    A score is simulated if its transformer row or any of its load rows in the window is.
    """
    transformers = source.transformers()
    if ev_exposure is not None and not ev_exposure.empty:
        stations = ev_exposure.set_index("transformer_id")["stations_within"]
        transformers = transformers.assign(
            ev_stations_within=transformers["transformer_id"].map(stations).fillna(0)
        )
    history = source.load(since=as_of - max(history_window, SCORING_WINDOW))
    history = history[history["ts"] <= as_of]  # rows that arrived later wait for the next run
    load = history[history["ts"] > as_of - SCORING_WINDOW]
    # A newly installed retrofit transformer needs a week of readings before it can be forecast;
    # until then it is left out of the run (the card says so) instead of failing every transformer.
    counts = load.groupby("transformer_id").size()
    load = load[load["transformer_id"].isin(counts[counts >= STEPS_PER_WEEK].index)]
    if load.empty:
        return Scored((), pd.DataFrame(columns=FORECAST_COLUMNS))
    weather_in = _weather_input(weather, transformers)
    optional: dict[str, Any] = {"history": history}
    if weather_in is not None:
        optional["weather"] = weather_in
    model = create("forecaster", forecaster)
    model = model.fit(load, **accepted(model.fit, 1, **optional))
    forecast = model.predict(load, STEPS_PER_DAY, **accepted(model.predict, 2, **optional))
    scorer = create("risk_scorer", risk_scorer).fit(load, transformers)
    outputs = scorer.score(forecast, transformers, **accepted(scorer.score, 2, **optional))
    load_simulated = load.groupby("transformer_id")["is_simulated"].any()
    scores = tuple(
        o.model_copy(
            update={
                "is_simulated": o.is_simulated or bool(load_simulated.get(o.transformer_id, False))
            }
        )
        for o in outputs
    )
    flags = pd.Series({s.transformer_id: s.is_simulated for s in scores}, dtype=bool)
    forecast = forecast.assign(
        is_simulated=forecast["transformer_id"].map(flags).fillna(True).astype(bool)
    )
    risk_features = ml_features.risk_features
    features = risk_features(
        forecast, "kw_pred", transformers, **accepted(risk_features, 3, **optional)
    )
    return Scored(scores, forecast, features, history)
