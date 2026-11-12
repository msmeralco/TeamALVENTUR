"""LightGBM load forecast, trained in notebooks/04 and exported to models/forecaster/lightgbm/.

One model for all transformers; every feature is at least one day old, so one call forecasts the
next 24 h for every transformer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Self

import numpy as np
import pandas as pd

from silip_ml.core.artifacts import Artifact, load_artifact
from silip_ml.core.config import get_ml_settings
from silip_ml.core.registry import register
from silip_ml.features import WeatherInput, load_features
from silip_ml.load.domain import forecast_frame, history_grid
from silip_ml.readings.domain import STEPS_PER_WEEK

TASK, NAME = "forecaster", "lightgbm"


@register(TASK, NAME)
class LightGBMForecaster:
    """Loads the exported booster; kept only if the backtest beats `seasonal_naive`."""

    name = NAME  # artifact folder; subclasses that only change the artifact override it

    def __init__(self, models_dir: Path | None = None) -> None:
        self._models_dir = models_dir or get_ml_settings().models_dir

    @property
    def artifact(self) -> Artifact:
        return load_artifact(Path(self._models_dir), TASK, self.name)

    def fit(self, load: pd.DataFrame) -> Self:
        return self  # trained in the notebooks; kept for callers that still call fit

    def predict(
        self, history: pd.DataFrame, horizon_steps: int, weather: WeatherInput | None = None
    ) -> pd.DataFrame:
        artifact = self.artifact
        max_horizon = int(artifact.metadata["max_horizon_steps"])
        if horizon_steps > max_horizon:
            raise ValueError(f"horizon_steps must be <= {max_horizon}")
        grid = history_grid(history, min_steps=STEPS_PER_WEEK)
        rows = grid.steps + np.arange(horizon_steps)
        params = artifact.metadata["feature_params"]
        x = load_features(grid, rows, artifact.features, params["holidays"], weather)
        kw_pred = np.asarray(
            artifact.booster.predict(x), dtype=np.float64
        )  # one call, all transformers
        return forecast_frame(grid, kw_pred, horizon_steps)
