"""The Forecaster port and the frame shapes it reads and returns."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol, Self

import numpy as np
import pandas as pd

from silip_ml.readings.domain import STEPS_PER_WEEK

STEP = pd.Timedelta("15min")
# Load history columns: transformer_id, ts, transformer_kw (plus extras, ignored).
# Forecast columns: transformer_id, ts, kw_pred.


class InsufficientHistoryError(ValueError):
    """Raised when a transformer has less history than a strategy needs."""


class Forecaster(Protocol):
    """Predicts transformer kW for the next `horizon_steps` 15-minute intervals."""

    def fit(self, load: pd.DataFrame) -> Self: ...

    def predict(self, history: pd.DataFrame, horizon_steps: int) -> pd.DataFrame: ...


def history_by_transformer(
    history: pd.DataFrame, min_steps: int = STEPS_PER_WEEK
) -> Iterator[tuple[str, pd.DatetimeIndex, np.ndarray]]:
    """Yield `(transformer_id, ts, kw)` per transformer, oldest interval first.

    Raises:
        InsufficientHistoryError: if a transformer has fewer than `min_steps` intervals.
    """
    for transformer_id, group in history.sort_values("ts").groupby("transformer_id"):
        kw = group["transformer_kw"].to_numpy()
        if len(kw) < min_steps:
            raise InsufficientHistoryError(f"{transformer_id}: {len(kw)} < {min_steps} intervals")
        yield str(transformer_id), pd.DatetimeIndex(group["ts"]), kw


def forecast_frame(transformer_id: str, last_ts: pd.Timestamp, kw_pred: np.ndarray) -> pd.DataFrame:
    """Forecast rows starting one step after `last_ts`."""
    steps = np.arange(1, len(kw_pred) + 1)
    return pd.DataFrame(
        {"transformer_id": transformer_id, "ts": last_ts + steps * STEP, "kw_pred": kw_pred}
    )
