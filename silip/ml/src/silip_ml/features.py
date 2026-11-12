"""Inference features, built for every transformer at once.

Definitions match `notebooks/_features.py`, where the models are trained. The export notebook
writes a parity sample to `models/<task>/<name>/parity/`; `tests/ml/test_parity.py` fails if these
functions stop reproducing it. Change a feature in both places, then re-export.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from silip_ml.readings.domain import ASSUMED_POWER_FACTOR, STEPS_PER_DAY, STEPS_PER_HOUR

STEP = pd.Timedelta("15min")


class UnknownFeatureError(KeyError):
    """metadata.json names a feature this package cannot build."""


@dataclass(frozen=True)
class Grid:
    """Values on a regular 15-minute grid: `values[step, transformer]`, NaN where missing."""

    transformer_ids: np.ndarray  # sorted, like pandas pivot columns
    start: pd.Timestamp
    values: np.ndarray

    @property
    def steps(self) -> int:
        return self.values.shape[0]

    def ts(self, rows: np.ndarray) -> pd.DatetimeIndex:
        return pd.DatetimeIndex(self.start + rows * STEP)


def to_grid(frame: pd.DataFrame, column: str) -> Grid:
    """Place `column` on the 15-minute grid from the first to the last `ts`, one column per transformer."""
    codes, ids = pd.factorize(frame["transformer_id"].astype(str), sort=True)  # sorted, like pivot
    ts = pd.DatetimeIndex(frame["ts"])
    start = ts.min()
    rows = np.asarray((ts - start) // STEP, dtype=np.int64)
    values = np.full((int(rows.max()) + 1, len(ids)), np.nan)
    values[rows, codes] = frame[column].to_numpy(dtype=np.float64)
    return Grid(np.asarray(ids, dtype=object), start, values)


def _past(grid: Grid, rows: np.ndarray, days: int) -> np.ndarray:
    """Values `days` days before each row, shape (rows, transformers); NaN before the grid starts."""
    source = rows - days * STEPS_PER_DAY
    out = np.full((len(rows), grid.values.shape[1]), np.nan)
    inside = (source >= 0) & (source < grid.steps)
    out[inside] = grid.values[source[inside]]
    return out


def load_features(
    grid: Grid, rows: np.ndarray, features: Sequence[str], holidays: Sequence[str]
) -> np.ndarray:
    """Feature matrix for `rows` of `grid`, ordered transformer by transformer, then by row.

    Raises:
        UnknownFeatureError: if `features` names something not defined here.
    """
    ts = grid.ts(rows)
    calendar = {
        "hour": np.asarray(ts.hour + ts.minute / 60, dtype=np.float64),
        "day_of_week": ts.day_of_week.to_numpy().astype(np.float64),
        "is_weekend": (ts.day_of_week.to_numpy() >= 5).astype(np.float64),
        "is_holiday": np.isin(ts.strftime("%Y-%m-%d"), list(holidays)).astype(np.float64),
    }
    columns = []
    for name in features:
        if name in calendar:
            column = np.repeat(calendar[name][:, None], len(grid.transformer_ids), axis=1)
        elif name.startswith("lag_") and name.endswith("d"):
            column = _past(grid, rows, int(name[4:-1]))
        else:
            raise UnknownFeatureError(name)
        columns.append(column.T.ravel())  # transformer-major
    return np.column_stack(columns)


def longest_run(over: np.ndarray) -> np.ndarray:
    """Longest run of True along the last axis, for every row at once."""
    over = np.atleast_2d(over)
    run = np.zeros(over.shape[0], dtype=np.int64)
    best = run.copy()
    for column in over.T:
        run = (run + 1) * column
        best = np.maximum(best, run)
    return best


RISK_COLUMNS = [
    "peak_load_pct",
    "mean_load_pct",
    "hours_over_100",
    "hours_over_110",
    "hours_over_90",
    "coverage_pct",
    "rated_kva",
]


def risk_features(
    forecast: pd.DataFrame, kw_column: str, transformers: pd.DataFrame
) -> pd.DataFrame:
    """One row per transformer from its forecast window, plus `peak_ts` and `is_simulated`.

    `transformers` needs `transformer_id, rated_kva, coverage_pct, is_simulated`. Transformers
    missing from it are dropped.
    """
    grid = to_grid(forecast, kw_column)
    info = transformers.assign(transformer_id=transformers["transformer_id"].astype(str))
    info = info.set_index("transformer_id").reindex(grid.transformer_ids)
    known = info["rated_kva"].notna().to_numpy()
    rated = info["rated_kva"].to_numpy(dtype=np.float64)
    # (transformers, steps), C-contiguous so each row's mean sums in the same order as the notebook's
    pct = np.ascontiguousarray(grid.values.T) / (rated[:, None] * ASSUMED_POWER_FACTOR)
    peak_step = np.nanargmax(np.where(np.isnan(pct), -np.inf, pct), axis=1)
    features = pd.DataFrame(
        {
            "transformer_id": grid.transformer_ids,
            "peak_load_pct": pct.max(axis=1),
            "peak_ts": grid.ts(peak_step),
            "mean_load_pct": pct.mean(axis=1),
            "hours_over_100": longest_run(pct > 1.0) / STEPS_PER_HOUR,
            "hours_over_110": longest_run(pct > 1.1) / STEPS_PER_HOUR,
            "hours_over_90": (pct > 0.9).sum(axis=1) / STEPS_PER_HOUR,
            "coverage_pct": info["coverage_pct"].to_numpy(dtype=np.float64),
            "rated_kva": rated,
            "is_simulated": info["is_simulated"].fillna(True).astype(bool).to_numpy(),
        }
    )
    return features[known].reset_index(drop=True)
