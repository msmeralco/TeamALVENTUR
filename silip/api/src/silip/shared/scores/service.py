"""Forecast and score every transformer once. Used by the batch job and the simulated-mode API."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from silip.shared.readings.domain import DataSource
from silip.shared.scores.domain import SCORING_WINDOW, Scored
from silip_ml.core.registry import create
from silip_ml.readings.domain import STEPS_PER_DAY, STEPS_PER_WEEK


def score_window(source: DataSource, as_of: datetime, forecaster: str, risk_scorer: str) -> Scored:
    """Forecast the 24 h after `as_of` from the `SCORING_WINDOW` before it, then score it.

    A score is simulated if its transformer row or any of its load rows in the window is.
    """
    transformers = source.transformers()
    load = source.load(since=as_of - SCORING_WINDOW)
    load = load[load["ts"] <= as_of]  # rows that arrived after as_of was read wait for the next run
    # A newly installed retrofit transformer needs a week of readings before it can be forecast;
    # until then it is left out of the run (the card says so) instead of failing every transformer.
    counts = load.groupby("transformer_id").size()
    load = load[load["transformer_id"].isin(counts[counts >= STEPS_PER_WEEK].index)]
    if load.empty:
        return Scored((), pd.DataFrame(columns=["transformer_id", "ts", "kw_pred", "is_simulated"]))
    forecast = create("forecaster", forecaster).fit(load).predict(load, STEPS_PER_DAY)
    outputs = (
        create("risk_scorer", risk_scorer).fit(load, transformers).score(forecast, transformers)
    )
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
    return Scored(scores, forecast)
