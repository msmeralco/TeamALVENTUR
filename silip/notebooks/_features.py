"""Feature definitions used to train SILIP's models. `03_features_and_preprocessing` explains them.

`silip_ml/features.py` re-implements these for inference. The export notebook writes a parity
sample and `tests/ml/test_parity.py` fails if the two ever disagree.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

STEPS_PER_DAY = 96
POWER_FACTOR = 0.9  # kVA rating to usable kW (silip-domain: load_pct = kW / (rated_kva * 0.9))

# Load forecast: every input is at least one day old, so one model forecasts the next 24 h.
LOAD_PARAMS = {"lag_days": [1, 2, 7], "same_slot_mean_days": [3, 7]}
# Chosen in 03 by time-series cross-validation; `load_features` also builds the other candidates.
LOAD_FEATURES = ["lag_1d", "lag_2d", "lag_7d", "hour", "day_of_week", "is_weekend", "is_holiday"]
# Risk: what the 24 h forecast says about each transformer, plus how well it is metered.
RISK_FEATURES = [
    "peak_load_pct", "mean_load_pct", "hours_over_100", "hours_over_110", "hours_over_90",
    "coverage_pct", "rated_kva",
]


def to_grid(load: pd.DataFrame, column: str = "transformer_kw", until: pd.Timestamp | None = None) -> pd.DataFrame:
    """Wide table: one row per 15-minute interval, one column per transformer. Gaps become NaN."""
    wide = load.pivot(index="ts", columns="transformer_id", values=column).sort_index()
    end = wide.index[-1] if until is None else until
    return wide.reindex(pd.date_range(wide.index[0], end, freq="15min"))


def same_slot_mean(grid: pd.DataFrame, days: int) -> pd.DataFrame:
    """Mean of the same 15-minute slot over the last `days` days, skipping missing ones."""
    total, count = 0.0, 0.0
    for d in range(1, days + 1):
        past = grid.shift(d * STEPS_PER_DAY)
        total = total + past.fillna(0.0)
        count = count + past.notna().astype(float)
    return total / count.where(count > 0)


def load_features(grid: pd.DataFrame, holidays: list[str]) -> pd.DataFrame:
    """Long table of features per (transformer, ts) on the grid. NaN where history is missing."""
    wide = {f"lag_{d}d": grid.shift(d * STEPS_PER_DAY) for d in LOAD_PARAMS["lag_days"]}
    for days in LOAD_PARAMS["same_slot_mean_days"]:
        wide[f"same_slot_mean_{days}d"] = same_slot_mean(grid, days)
    long = pd.concat({name: frame.stack(future_stack=True) for name, frame in wide.items()}, axis=1)
    long.index = long.index.set_names(["ts", "transformer_id"])
    long = long.reset_index()
    ts = pd.DatetimeIndex(long["ts"])
    long["hour"] = ts.hour + ts.minute / 60
    long["day_of_week"] = ts.day_of_week.astype(float)
    long["is_weekend"] = (ts.day_of_week >= 5).astype(float)
    long["is_holiday"] = np.isin(ts.strftime("%Y-%m-%d"), holidays).astype(float)
    return long.sort_values(["transformer_id", "ts"], ignore_index=True)


def longest_run(over: np.ndarray) -> int:
    """Longest stretch of consecutive True values."""
    best = run = 0
    for flag in over:
        run = run + 1 if flag else 0
        best = max(best, run)
    return best


def risk_features(forecast: pd.DataFrame, transformers: pd.DataFrame) -> pd.DataFrame:
    """One row per transformer from its 24 h forecast (`kw_pred`)."""
    rows = []
    info = transformers.set_index("transformer_id")
    for tid, group in forecast.sort_values("ts").groupby("transformer_id"):
        rated = float(info.loc[tid, "rated_kva"])
        pct = group["kw_pred"].to_numpy() / (rated * POWER_FACTOR)
        rows.append({
            "transformer_id": tid,
            "peak_load_pct": pct.max(),
            "mean_load_pct": pct.mean(),
            "hours_over_100": longest_run(pct > 1.0) / 4,
            "hours_over_110": longest_run(pct > 1.1) / 4,
            "hours_over_90": (pct > 0.9).sum() / 4,
            "coverage_pct": float(info.loc[tid, "coverage_pct"]),
            "rated_kva": rated,
        })
    return pd.DataFrame(rows)


def trip_labels(load: pd.DataFrame, transformers: pd.DataFrame, column: str = "true_kw") -> pd.DataFrame:
    """Ground truth per (transformer, day): load above 110% of rating for 3 h in a row (silip-domain).

    `trip_ts` is when the 3-hour run completes, so `trip_ts - day` is the warning lead a 00:00
    score would have given.
    """
    grid = to_grid(load, column)
    rated = transformers.set_index("transformer_id").loc[grid.columns, "rated_kva"].to_numpy()
    over = grid.to_numpy() / (rated * POWER_FACTOR) > 1.1  # NaN compares False: a gap breaks a run
    rows = []
    for day, idx in pd.Series(np.arange(len(grid)), index=grid.index).groupby(grid.index.normalize()):
        block = over[idx.to_numpy()]
        for j, tid in enumerate(grid.columns):
            run, trip_ts = 0, pd.NaT
            for i, flag in enumerate(block[:, j]):
                run = run + 1 if flag else 0
                if run == 12:
                    trip_ts = grid.index[idx.iloc[i]]
                    break
            rows.append({"transformer_id": tid, "day": day, "tripped": pd.notna(trip_ts), "trip_ts": trip_ts})
    return pd.DataFrame(rows)
