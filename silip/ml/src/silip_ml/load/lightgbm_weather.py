"""LightGBM load forecast with day-ahead weather, trained in notebooks/04 and exported by 06 to
models/forecaster/lightgbm_weather/.

The lags and calendar of `lightgbm` plus the forecast heat index at the target hour, its change
from the observed hour a day earlier, and forecast rain (ADR 0006). Weather rows are read only if
issued by 00:00 (Manila) of the day the history ends; without weather those inputs are missing and
LightGBM routes them down its missing-value branch, so callers that lose the feed should fall back
to `lightgbm`.
"""

from __future__ import annotations

from silip_ml.core.registry import register
from silip_ml.load.lightgbm import TASK, LightGBMForecaster


@register(TASK, "lightgbm_weather")
class LightGBMWeatherForecaster(LightGBMForecaster):
    """Same inference as `lightgbm`; the artifact's feature list adds the weather inputs."""

    name = "lightgbm_weather"
