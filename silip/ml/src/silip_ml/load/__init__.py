"""Load forecasting. Importing this package registers every forecaster."""

from silip_ml.load import lightgbm, lightgbm_weather, seasonal_naive  # noqa: F401  (registers strategies)
