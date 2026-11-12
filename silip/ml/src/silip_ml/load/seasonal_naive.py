"""Baseline: the same 15-minute interval last week."""

from __future__ import annotations

from typing import Self

import numpy as np
import pandas as pd

from silip_ml.core.registry import register
from silip_ml.load.domain import forecast_frame, history_by_transformer
from silip_ml.readings.domain import STEPS_PER_WEEK


@register("forecaster", "seasonal_naive")
class SeasonalNaive:
    """kW at t is predicted as kW at t minus 7 days. Needs no training."""

    def fit(self, load: pd.DataFrame) -> Self:
        return self

    def predict(self, history: pd.DataFrame, horizon_steps: int) -> pd.DataFrame:
        frames = []
        for transformer_id, ts, kw in history_by_transformer(history):
            last_week = kw[-STEPS_PER_WEEK:]
            kw_pred = last_week[np.arange(horizon_steps) % STEPS_PER_WEEK]
            frames.append(forecast_frame(transformer_id, ts[-1], kw_pred))
        return pd.concat(frames, ignore_index=True)
