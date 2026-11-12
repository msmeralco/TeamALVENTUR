"""LightGBM on day-ago and week-ago lags plus time of day. One model for all transformers."""

from __future__ import annotations

from typing import Self

import lightgbm as lgb
import numpy as np
import pandas as pd

from silip_ml.core.registry import register
from silip_ml.load.domain import STEP, forecast_frame, history_by_transformer
from silip_ml.readings.domain import STEPS_PER_DAY, STEPS_PER_WEEK

MAX_HORIZON_STEPS = STEPS_PER_DAY  # the day-ago lag must already be observed


def _features(ts: pd.DatetimeIndex, lag_day: np.ndarray, lag_week: np.ndarray) -> np.ndarray:
    hour = ts.hour + ts.minute / 60
    return np.column_stack([lag_day, lag_week, hour, ts.day_of_week])


@register("forecaster", "lightgbm")
class LightGBMForecaster:
    """Gradient-boosted trees; kept only if the backtest beats `seasonal_naive`."""

    def __init__(self, n_estimators: int = 200, learning_rate: float = 0.05) -> None:
        self._model = lgb.LGBMRegressor(
            n_estimators=n_estimators, learning_rate=learning_rate, min_child_samples=5, verbose=-1
        )

    def fit(self, load: pd.DataFrame) -> Self:
        features, targets = [], []
        for _, ts, kw in history_by_transformer(load, min_steps=STEPS_PER_WEEK + 1):
            i = np.arange(STEPS_PER_WEEK, len(kw))
            features.append(_features(ts[i], kw[i - STEPS_PER_DAY], kw[i - STEPS_PER_WEEK]))
            targets.append(kw[i])
        self._model.fit(np.vstack(features), np.concatenate(targets))
        return self

    def predict(self, history: pd.DataFrame, horizon_steps: int) -> pd.DataFrame:
        if horizon_steps > MAX_HORIZON_STEPS:
            raise ValueError(f"horizon_steps must be <= {MAX_HORIZON_STEPS}")
        frames = []
        for transformer_id, ts, kw in history_by_transformer(history):
            k = np.arange(horizon_steps)
            future_ts = ts[-1] + (k + 1) * STEP
            n = len(kw)
            x = _features(
                pd.DatetimeIndex(future_ts), kw[n - STEPS_PER_DAY + k], kw[n - STEPS_PER_WEEK + k]
            )
            frames.append(
                forecast_frame(transformer_id, ts[-1], np.asarray(self._model.predict(x)))
            )
        return pd.concat(frames, ignore_index=True)
