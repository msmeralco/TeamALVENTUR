"""LightGBM risk classifier with weather, EV and clamp-health inputs, trained in notebooks/05 and
exported by 06 to models/risk_scorer/lightgbm_weather_ev/ (ADR 0007).

Trained on features of out-of-sample `lightgbm_weather` day-ahead forecasts, labeled by the trip
rule. Reasons come from the booster's per-feature contributions (`pred_contrib=True`): the three
largest positive ones, written with the templates in `risk.domain`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from silip_ml.core.registry import register
from silip_ml.features import WeatherInput, risk_features
from silip_ml.risk.domain import RiskOutput, contribution_drivers, risk_output
from silip_ml.risk.lightgbm import TASK, LightGBMScorer, _tiers


@register(TASK, "lightgbm_weather_ev")
class LightGBMWeatherEvScorer(LightGBMScorer):
    """Pass `weather` and `history` to `score`; without them those inputs are missing (NaN)."""

    name = "lightgbm_weather_ev"

    def contributions(self, features: pd.DataFrame) -> np.ndarray:
        """Per-feature contributions in log-odds, shape (rows, features); the bias column dropped."""
        artifact = self.artifact
        x = features[artifact.features].to_numpy(dtype=np.float64)
        return np.asarray(artifact.booster.predict(x, pred_contrib=True), dtype=np.float64)[:, :-1]

    def score(
        self,
        forecast: pd.DataFrame,
        transformers: pd.DataFrame,
        weather: WeatherInput | None = None,
        history: pd.DataFrame | None = None,
    ) -> list[RiskOutput]:
        features = risk_features(forecast, "kw_pred", transformers, weather, history)
        thresholds = self.artifact.metadata["thresholds"]
        tiers = _tiers(self.probability(features), thresholds["critical"], thresholds["watch"])
        names = self.artifact.features
        return [
            risk_output(
                row, tier, contribution_drivers(row, dict(zip(names, contrib, strict=True)))
            )
            for row, tier, contrib in zip(
                features.to_dict("records"), tiers, self.contributions(features), strict=True
            )
        ]
