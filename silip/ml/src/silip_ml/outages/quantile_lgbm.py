"""LightGBM quantile regression (P10, P50, P90) on cause and start time."""

from __future__ import annotations

from typing import Self

import lightgbm as lgb
import numpy as np
import pandas as pd

from silip_ml.core.registry import register
from silip_ml.outages.median_by_cause import QUANTILES


@register("eta_estimator", "quantile_lgbm")
class QuantileLGBM:
    """One quantile model per output column."""

    def __init__(self) -> None:
        self._causes: list[str] = []
        self._models = {
            name: lgb.LGBMRegressor(
                objective="quantile", alpha=q, n_estimators=100, min_child_samples=5, verbose=-1
            )
            for name, q in QUANTILES.items()
        }

    def _features(self, outages: pd.DataFrame) -> np.ndarray:
        cause = outages["cause"].map({c: i for i, c in enumerate(self._causes)}).fillna(-1)
        start = pd.DatetimeIndex(outages["start_ts"])
        return np.column_stack([cause, start.hour, start.day_of_week])

    def fit(self, outages: pd.DataFrame) -> Self:
        self._causes = sorted(outages["cause"].unique())
        x = self._features(outages)
        for model in self._models.values():
            model.fit(x, outages["duration_min"].to_numpy())
        return self

    def predict(self, outages: pd.DataFrame) -> pd.DataFrame:
        x = self._features(outages)
        result = outages[["outage_id"]].copy()
        for name, model in self._models.items():
            result[name] = np.clip(np.asarray(model.predict(x)), 0, None)
        # Quantile models can cross; keep P10 <= P50 <= P90.
        result[list(QUANTILES)] = np.sort(result[list(QUANTILES)].to_numpy(), axis=1)
        return result
