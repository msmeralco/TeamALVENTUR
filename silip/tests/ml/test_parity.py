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
from silip_ml.features import load_features, risk_features
from silip_ml.load.domain import history_grid
from silip_ml.load.lightgbm import LightGBMForecaster
from silip_ml.risk.lightgbm import LightGBMScorer

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
