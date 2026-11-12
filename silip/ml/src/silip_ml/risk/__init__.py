"""Risk scoring. Importing this package registers every scorer."""

from silip_ml.risk import lightgbm, lightgbm_weather_ev, rules  # noqa: F401  (registers strategies)
