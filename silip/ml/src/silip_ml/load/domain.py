"""The Forecaster port and the frame shapes it reads and returns."""

from __future__ import annotations

from typing import Protocol, Self

import numpy as np
import pandas as pd

from silip_ml.features import STEP, Grid, to_grid
from silip_ml.readings.domain import STEPS_PER_WEEK

__all__ = ["STEP", "Forecaster", "InsufficientHistoryError", "forecast_frame", "history_grid"]
# Load history columns: transformer_id, ts, transformer_kw (plus extras, ignored).
# Forecast columns: transformer_id, ts, kw_pred. Every transformer is forecast from the latest
# `ts` in the history, even if its own readings stopped earlier.


class InsufficientHistoryError(ValueError):
    """Raised when the history is shorter than a strategy needs."""


class Forecaster(Protocol):
    """Predicts transformer kW for the next `horizon_steps` 15-minute intervals.

    `fit` is a no-op kept so callers written for trained-on-request models still work; trained
    strategies load an exported artifact instead. Remove it once no caller uses it.
    """

    def fit(self, load: pd.DataFrame) -> Self: ...

    def predict(self, history: pd.DataFrame, horizon_steps: int) -> pd.DataFrame: ...


def history_grid(history: pd.DataFrame, min_steps: int = STEPS_PER_WEEK) -> Grid:
    """`transformer_kw` on the 15-minute grid, every transformer at once.

    Raises:
        InsufficientHistoryError: if the history spans fewer than `min_steps` intervals.
    """
    grid = to_grid(history, "transformer_kw")
    if grid.steps < min_steps:
        raise InsufficientHistoryError(f"history spans {grid.steps} < {min_steps} intervals")
    return grid


def forecast_frame(grid: Grid, kw_pred: np.ndarray, horizon_steps: int) -> pd.DataFrame:
    """Forecast rows after the grid ends; `kw_pred` is transformer-major, `horizon_steps` each."""
    future_ts = grid.ts(grid.steps + np.arange(horizon_steps))
    return pd.DataFrame(
        {
            "transformer_id": np.repeat(grid.transformer_ids, horizon_steps),
            "ts": np.tile(future_ts, len(grid.transformer_ids)),
            "kw_pred": kw_pred,
        }
    )
