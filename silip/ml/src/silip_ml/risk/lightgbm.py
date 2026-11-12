"""LightGBM classifier on daily window features, trained on past days' actual load.

Training uses each past day's actual load as the window and that day's trip as the label;
scoring uses the forecast window. SHAP reasons come later; reasons are the rule features for now.
"""

from __future__ import annotations

from typing import Self

import lightgbm as lgb
import numpy as np
import pandas as pd

from silip_ml.core.registry import register
from silip_ml.readings.domain import load_pct
from silip_ml.risk.domain import RiskOutput, Tier, is_trip, risk_output, window_features

FEATURES = ["peak_load_pct", "hours_over_100", "coverage_pct"]
CRITICAL_PROBABILITY, WATCH_PROBABILITY = 0.5, 0.2


def _daily_examples(load: pd.DataFrame, transformers: pd.DataFrame) -> pd.DataFrame:
    day = load["ts"].dt.normalize()
    rows = []
    for _, window in load.groupby(day):
        features = window_features(window, "transformer_kw", transformers)
        rated = transformers.set_index("transformer_id")["rated_kva"]
        trips = {
            tid: is_trip(load_pct(g.sort_values("ts")["transformer_kw"].to_numpy(), rated[tid]))
            for tid, g in window.groupby("transformer_id")
        }
        rows.append(features.assign(label=features["transformer_id"].map(trips)))
    return pd.concat(rows, ignore_index=True)


@register("risk_scorer", "lightgbm")
class LightGBMScorer:
    """Kept only if the backtest beats `rules` on recall without more false alarms."""

    def __init__(self) -> None:
        self._model = lgb.LGBMClassifier(n_estimators=100, min_child_samples=5, verbose=-1)
        self._constant: float | None = None

    def fit(self, load: pd.DataFrame, transformers: pd.DataFrame) -> Self:
        examples = _daily_examples(load, transformers)
        labels = examples["label"].astype(int).to_numpy()
        if len(np.unique(labels)) < 2:  # one class only: nothing to learn
            self._constant = float(labels[0]) if len(labels) else 0.0
        else:
            self._model.fit(examples[FEATURES].to_numpy(), labels)
        return self

    def _probability(self, features: pd.DataFrame) -> np.ndarray:
        if self._constant is not None:
            return np.full(len(features), self._constant)
        return np.asarray(self._model.predict_proba(features[FEATURES].to_numpy()))[:, 1]

    def score(self, forecast: pd.DataFrame, transformers: pd.DataFrame) -> list[RiskOutput]:
        features = window_features(forecast, "kw_pred", transformers)
        rows = features.to_dict("records")
        return [
            risk_output(row, _tier(probability))
            for row, probability in zip(rows, self._probability(features), strict=True)
        ]


def _tier(probability: float) -> Tier:
    if probability >= CRITICAL_PROBABILITY:
        return "Critical"
    return "Watch" if probability >= WATCH_PROBABILITY else "OK"
