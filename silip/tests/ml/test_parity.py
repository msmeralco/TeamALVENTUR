"""Train/serve parity: silip_ml must rebuild exactly what the export notebook computed.

The notebooks train with `notebooks/_features.py`; `silip_ml.features` re-implements the same
definitions for inference. `notebooks/06_evaluate_and_export.ipynb` writes, next to each model,
input rows, the features it built from them and the predictions it expected. If a feature
definition changes in one place only, these tests fail.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from silip_ml.core.config import get_ml_settings
from silip_ml.features import load_features, risk_features, weather_input
from silip_ml.load.domain import history_grid
from silip_ml.load.lightgbm import LightGBMForecaster
from silip_ml.load.lightgbm_weather import LightGBMWeatherForecaster
from silip_ml.risk.lightgbm import LightGBMScorer
from silip_ml.risk.lightgbm_weather_ev import LightGBMWeatherEvScorer

MODELS = get_ml_settings().models_dir


def _read(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, float_precision="round_trip")  # exact float64 round trip
    if "ts" in frame:
        frame["ts"] = pd.to_datetime(frame["ts"], format="ISO8601")
    return frame


def _parity(task: str, file: str) -> pd.DataFrame:
    path = MODELS / task / "lightgbm" / "parity" / file
    if not path.exists():
        pytest.fail(f"{path} missing; run notebooks/06_evaluate_and_export.ipynb")
    return _read(path)


def test_load_features_match_the_notebook():
    history = _parity("forecaster", "input_load.csv")
    expected = _parity("forecaster", "features.csv")
    forecaster = LightGBMForecaster()
    metadata = forecaster.artifact.metadata
    grid = history_grid(history)
    horizon = len(expected) // len(grid.transformer_ids)
    rows = grid.steps + np.arange(horizon)
    actual = load_features(grid, rows, metadata["features"], metadata["feature_params"]["holidays"])
    np.testing.assert_array_equal(actual, expected[metadata["features"]].to_numpy())


def test_load_predictions_match_the_notebook():
    history = _parity("forecaster", "input_load.csv")
    expected = _parity("forecaster", "predictions.csv")
    forecast = LightGBMForecaster().predict(
        history, len(expected) // history["transformer_id"].nunique()
    )
    assert forecast["transformer_id"].tolist() == expected["transformer_id"].tolist()
    assert (forecast["ts"].to_numpy() == expected["ts"].to_numpy()).all()
    np.testing.assert_array_equal(forecast["kw_pred"].to_numpy(), expected["kw_pred"].to_numpy())


def test_risk_features_and_scores_match_the_notebook():
    forecast = _parity("risk_scorer", "input_forecast.csv")
    transformers = _parity("risk_scorer", "transformers.csv")
    expected_features = _parity("risk_scorer", "features.csv")
    expected = _parity("risk_scorer", "predictions.csv")
    scorer = LightGBMScorer()
    features = risk_features(forecast, "kw_pred", transformers)
    names = scorer.artifact.features
    assert features["transformer_id"].tolist() == expected_features["transformer_id"].tolist()
    np.testing.assert_array_equal(features[names].to_numpy(), expected_features[names].to_numpy())
    np.testing.assert_array_equal(scorer.probability(features), expected["score"].to_numpy())
    tiers = [o.tier for o in scorer.score(forecast, transformers)]
    assert tiers == expected["tier"].tolist()


def _parity_of(task: str, name: str, file: str) -> pd.DataFrame:
    path = MODELS / task / name / "parity" / file
    if not path.exists():
        pytest.fail(f"{path} missing; run notebooks/06_evaluate_and_export.ipynb")
    frame = _read(path)
    if "issued_at" in frame:
        frame["issued_at"] = pd.to_datetime(frame["issued_at"], format="ISO8601")
    return frame


def test_weather_load_features_and_predictions_match_the_notebook():
    task, name = "forecaster", "lightgbm_weather"
    history = _parity_of(task, name, "input_load.csv")
    weather = weather_input(
        _parity_of(task, name, "input_weather.csv"), _parity_of(task, name, "transformers.csv")
    )
    expected = _parity_of(task, name, "features.csv")
    forecaster = LightGBMWeatherForecaster()
    metadata = forecaster.artifact.metadata
    grid = history_grid(history)
    horizon = len(expected) // len(grid.transformer_ids)
    rows = grid.steps + np.arange(horizon)
    holidays = metadata["feature_params"]["holidays"]
    actual = load_features(grid, rows, metadata["features"], holidays, weather)
    np.testing.assert_array_equal(actual, expected[metadata["features"]].to_numpy())
    predictions = _parity_of(task, name, "predictions.csv")
    forecast = forecaster.predict(history, horizon, weather)
    np.testing.assert_array_equal(forecast["kw_pred"].to_numpy(), predictions["kw_pred"].to_numpy())


def test_weather_ev_risk_features_scores_and_contributions_match_the_notebook():
    task, name = "risk_scorer", "lightgbm_weather_ev"
    forecast = _parity_of(task, name, "input_forecast.csv")
    history = _parity_of(task, name, "input_load.csv")
    transformers = _parity_of(task, name, "transformers.csv")
    weather = weather_input(_parity_of(task, name, "input_weather.csv"), transformers)
    expected_features = _parity_of(task, name, "features.csv")
    expected = _parity_of(task, name, "predictions.csv")
    contributions = _parity_of(task, name, "contributions.csv")
    scorer = LightGBMWeatherEvScorer()
    names = scorer.artifact.features
    features = risk_features(forecast, "kw_pred", transformers, weather, history)
    assert features["transformer_id"].tolist() == expected_features["transformer_id"].tolist()
    np.testing.assert_array_equal(features[names].to_numpy(), expected_features[names].to_numpy())
    np.testing.assert_array_equal(scorer.probability(features), expected["score"].to_numpy())
    np.testing.assert_array_equal(scorer.contributions(features), contributions[names].to_numpy())
    outputs = scorer.score(forecast, transformers, weather, history)
    assert [o.tier for o in outputs] == expected["tier"].tolist()
    for output in outputs:
        assert 1 <= len(output.reasons) <= 3
        assert all("Open-Meteo" not in reason for reason in output.reasons)  # simulated weather
