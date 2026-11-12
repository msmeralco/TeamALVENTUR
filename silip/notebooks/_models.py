"""Training helpers shared by notebooks 04 to 06. Short on purpose; the notebooks explain each step."""

from __future__ import annotations

import json

import lightgbm as lgb
import numpy as np
import pandas as pd
from _data import ROOT
from _features import LOAD_FEATURES, load_features, risk_features, to_grid

RESULTS_DIR = ROOT / "notebooks" / "results"
SEED = 7
DAYS_PER_MONTH = 30


def load_table(load: pd.DataFrame, holidays: list[str]) -> pd.DataFrame:
    """Features plus the target `transformer_kw` for every (transformer, interval) on the grid."""
    grid = to_grid(load)
    table = load_features(grid, holidays)
    target = grid.stack(future_stack=True).rename("transformer_kw").reset_index()
    target.columns = ["ts", "transformer_id", "transformer_kw"]
    return table.merge(target, on=["transformer_id", "ts"])


def fit_load_model(train: pd.DataFrame, params: dict, features: list[str] = LOAD_FEATURES) -> lgb.LGBMRegressor:
    """LightGBM on rows with a known target; missing feature values stay NaN (LightGBM routes them)."""
    rows = train.dropna(subset=["transformer_kw"])
    model = lgb.LGBMRegressor(**params, random_state=SEED, deterministic=True, force_row_wise=True, verbose=-1)
    return model.fit(rows[features].to_numpy(dtype=np.float64), rows["transformer_kw"].to_numpy())


def day_ahead(model: lgb.LGBMRegressor, table: pd.DataFrame, features: list[str] = LOAD_FEATURES) -> pd.DataFrame:
    """Forecast for every row of `table`. Valid as a 00:00 day-ahead forecast: every input is at least 1 day old."""
    return table[["transformer_id", "ts"]].assign(
        kw_pred=model.predict(table[features].to_numpy(dtype=np.float64))
    )


def recall_and_false_alarms(flagged: pd.Series, tripped: pd.Series) -> dict:
    """Backtest metrics over (transformer, day) windows: recall of trips and false alarms per transformer-month."""
    flagged, tripped = flagged.astype(bool), tripped.astype(bool)
    trips = int(tripped.sum())
    return {
        "recall": (flagged & tripped).sum() / trips if trips else float("nan"),
        "false_alarms_per_tx_month": (flagged & ~tripped).sum() / len(flagged) * DAYS_PER_MONTH,
        "trips": trips,
        "windows": len(flagged),
    }


def save_result(name: str, payload: dict) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / f"{name}.json").write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def read_result(name: str) -> dict:
    return json.loads((RESULTS_DIR / f"{name}.json").read_text(encoding="utf-8"))


def rolling_day_ahead(table: pd.DataFrame, params: dict, first_day: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Day-ahead forecasts for every day in [first_day, end), refitting each week on all earlier days.

    These are the forecasts the risk model trains on: out of sample, like the ones it scores.
    """
    frames, origin = [], first_day
    while origin < end:
        stop = min(origin + pd.Timedelta(days=7), end)
        model = fit_load_model(table[table["ts"] < origin], params)
        frames.append(day_ahead(model, table[(table["ts"] >= origin) & (table["ts"] < stop)]))
        origin = stop
    return pd.concat(frames, ignore_index=True)


def risk_examples(forecasts: pd.DataFrame, transformers: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    """One row per (transformer, day): features of that day's 24 h forecast, plus the trip label."""
    days = forecasts["ts"].dt.normalize()
    frames = [risk_features(f, transformers).assign(day=day) for day, f in forecasts.groupby(days)]
    return pd.concat(frames, ignore_index=True).merge(labels, on=["transformer_id", "day"])
