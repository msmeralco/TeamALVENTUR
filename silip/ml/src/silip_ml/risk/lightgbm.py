"""LightGBM risk classifier, trained in notebooks/05 and exported to models/risk_scorer/lightgbm/.

It was trained on features of day-ahead forecasts (not of actual load), labeled by the trip rule,
so it scores the same kind of window it sees here. Tier thresholds come from metadata.json.
Reasons are the rule features for now; SHAP reasons come later.
"""

from __future__ import annotations

from pathlib import Path
from typing import Self

import numpy as np
import pandas as pd

from silip_ml.core.artifacts import Artifact, load_artifact
from silip_ml.core.config import get_ml_settings
from silip_ml.core.registry import register
from silip_ml.features import WeatherInput, risk_features
from silip_ml.risk.domain import RiskOutput, Tier, risk_output

TASK, NAME = "risk_scorer", "lightgbm"


@register(TASK, NAME)
class LightGBMScorer:
    """Kept only if the backtest beats `rules` on recall without more false alarms."""

    name = NAME  # artifact folder; subclasses that only change the artifact override it

    def __init__(self, models_dir: Path | None = None) -> None:
        self._models_dir = models_dir or get_ml_settings().models_dir

    @property
    def artifact(self) -> Artifact:
        return load_artifact(Path(self._models_dir), TASK, self.name)

    def fit(self, load: pd.DataFrame, transformers: pd.DataFrame) -> Self:
        return self  # trained in the notebooks; kept for callers that still call fit

    def probability(self, features: pd.DataFrame) -> np.ndarray:
        """Trip probability per row of `risk_features`, one call for all transformers."""
        artifact = self.artifact
        x = features[artifact.features].to_numpy(dtype=np.float64)
        return np.asarray(artifact.booster.predict(x), dtype=np.float64)

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
        return [
            risk_output(row, tier)
            for row, tier in zip(features.to_dict("records"), tiers, strict=True)
        ]


def _tiers(probability: np.ndarray, critical: float, watch: float) -> list[Tier]:
    return ["Critical" if p >= critical else "Watch" if p >= watch else "OK" for p in probability]
