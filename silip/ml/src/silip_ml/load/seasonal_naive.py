"""Baseline: the same 15-minute interval last week."""

from __future__ import annotations

from typing import Self

import numpy as np
import pandas as pd

from silip_ml.core.registry import register
from silip_ml.features import WeatherInput
from silip_ml.load.domain import forecast_frame, history_grid
from silip_ml.readings.domain import STEPS_PER_WEEK


@register("forecaster", "seasonal_naive")
class SeasonalNaive:
    """kW at t is predicted as kW at t minus 7 days. Needs no training.

    A missing interval last week (outage, offline clamps) falls back to that transformer's
    mean over last week.
    """

    def fit(self, load: pd.DataFrame) -> Self:
        return self

    def predict(
        self, history: pd.DataFrame, horizon_steps: int, weather: WeatherInput | None = None
    ) -> pd.DataFrame:
        grid = history_grid(history)
        last_week = grid.values[-STEPS_PER_WEEK:]  # (steps, transformers)
        kw_pred = last_week[np.arange(horizon_steps) % STEPS_PER_WEEK]
        seen = ~np.isnan(last_week)
        fallback = np.where(seen, last_week, 0.0).sum(axis=0) / np.maximum(seen.sum(axis=0), 1)
        kw_pred = np.where(np.isnan(kw_pred), fallback, kw_pred)
        return forecast_frame(grid, kw_pred.T.ravel(), horizon_steps)
