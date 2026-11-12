"""Baseline: Critical when forecast load stays above 100% for 2 h (docs/SPEC.md#models)."""

from __future__ import annotations

from typing import Self

import pandas as pd

from silip_ml.core.registry import register
from silip_ml.readings.domain import STEPS_PER_HOUR
from silip_ml.risk.domain import (
    CRITICAL_MIN_STEPS,
    WATCH_LOAD_PCT,
    RiskOutput,
    Row,
    Tier,
    risk_output,
    window_features,
)


def tier_for(row: Row) -> Tier:
    if row["hours_over_100"] * STEPS_PER_HOUR >= CRITICAL_MIN_STEPS:
        return "Critical"
    return "Watch" if row["peak_load_pct"] >= WATCH_LOAD_PCT else "OK"


@register("risk_scorer", "rules")
class RuleScorer:
    """Thresholds only. Confidence equals metering coverage."""

    def fit(self, load: pd.DataFrame, transformers: pd.DataFrame) -> Self:
        return self

    def score(self, forecast: pd.DataFrame, transformers: pd.DataFrame) -> list[RiskOutput]:
        features = window_features(forecast, "kw_pred", transformers)
        return [risk_output(row, tier_for(row)) for row in features.to_dict("records")]
