"""Baseline: past restoration times for the same cause (P10, median, P90)."""

from __future__ import annotations

from typing import Self

import pandas as pd

from silip_ml.core.registry import register

QUANTILES = {"eta_p10_min": 0.1, "eta_p50_min": 0.5, "eta_p90_min": 0.9}


@register("eta_estimator", "median_by_cause")
class MedianByCause:
    """Unknown causes fall back to all past outages."""

    def __init__(self) -> None:
        self._by_cause: pd.DataFrame | None = None
        self._overall: dict[str, float] = {}

    def fit(self, outages: pd.DataFrame) -> Self:
        grouped = outages.groupby("cause")["duration_min"]
        self._by_cause = pd.DataFrame({name: grouped.quantile(q) for name, q in QUANTILES.items()})
        self._overall = {
            name: float(outages["duration_min"].quantile(q)) for name, q in QUANTILES.items()
        }
        return self

    def predict(self, outages: pd.DataFrame) -> pd.DataFrame:
        if self._by_cause is None:
            raise RuntimeError("call fit() first")
        estimates = outages[["outage_id", "cause"]].join(self._by_cause, on="cause")
        return estimates.drop(columns="cause").fillna(self._overall)
