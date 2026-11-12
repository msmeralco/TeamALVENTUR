"""Load forecast metric for the backtest."""

from __future__ import annotations

import pandas as pd


def mae_kw(forecast: pd.DataFrame, actual: pd.DataFrame) -> tuple[float, int]:
    """Mean absolute error in kW over matched intervals, and how many intervals matched."""
    joined = forecast.merge(actual, on=["transformer_id", "ts"])
    return float((joined["kw_pred"] - joined["transformer_kw"]).abs().mean()), len(joined)
