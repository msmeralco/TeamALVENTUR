"""Feature definitions used to train SILIP's models. `03_features_and_preprocessing` explains them.

`silip_ml/features.py` re-implements these for inference. The export notebook writes a parity
sample and `tests/ml/test_parity.py` fails if the two ever disagree.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from _weather import cell_id

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
# Weather (ADR 0006) and EV exposure (ADR 0007): the `lightgbm_weather` and `lightgbm_weather_ev` models.
LOCAL_TZ = "Asia/Manila"  # forecasts are issued at 00:00 Manila time
WEATHER_FEATURES = ["hi_fcst_c", "hi_fcst_minus_lag1d_c", "rain_fcst_mm"]
LOAD_FEATURES_WEATHER = LOAD_FEATURES + WEATHER_FEATURES
RISK_FEATURES_WEATHER_EV = RISK_FEATURES + ["heat_index_max_c", "ev_evening_step_kw", "ev_stations_within", "reporting_pct"]
EV_STATION_RADIUS_M = 1000  # [VERIFY] same constant as silip_ml.ev
EARTH_RADIUS_M = 6_371_000.0
EVENING_START_HOUR = 20  # EV charging starts from 8 PM in the simulator (silip-domain)


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


# --- Weather (ADR 0006) -----------------------------------------------------------------------

def transformer_cells(transformers: pd.DataFrame) -> dict[str, str]:
    """Weather cell of each transformer with a location."""
    located = transformers.dropna(subset=["lat", "lon"])
    return {str(t): cell_id(float(a), float(o)) for t, a, o in zip(located["transformer_id"], located["lat"], located["lon"])}


def _utc(values) -> np.ndarray:
    """Naive UTC datetime64[ns], so every time zone compares."""
    return pd.DatetimeIndex(pd.to_datetime(values, utc=True)).tz_localize(None).as_unit("ns").to_numpy()


def _latest_issued(weather: pd.DataFrame, kind: str, column: str, cells, hours, cutoff) -> np.ndarray:
    """`column` of the latest `kind` row issued at or before each query's cutoff; NaN if none."""
    right = weather.loc[weather["kind"] == kind]
    right = pd.DataFrame({
        "cell_id": right["cell_id"].astype(str).to_numpy(), "ts": _utc(right["ts"]),
        "issued_at": _utc(right["issued_at"]), "value": right[column].to_numpy(dtype=np.float64),
    }).sort_values("issued_at", kind="stable")
    left = pd.DataFrame({"cell_id": cells, "ts": hours, "cutoff": cutoff, "i": np.arange(len(cells))}).sort_values("cutoff", kind="stable")
    merged = pd.merge_asof(left, right, left_on="cutoff", right_on="issued_at", by=["cell_id", "ts"])
    return merged.sort_values("i")["value"].to_numpy(dtype=np.float64)


def weather_at(weather: pd.DataFrame, cells, ts: pd.DatetimeIndex, cutoff: pd.DatetimeIndex) -> dict[str, np.ndarray]:
    """Forecast heat index and rain at each target hour, and the change from the observed hour a day
    earlier, reading only rows issued at or before each query's cutoff. Observed (`archive`) rows are
    read only for the hour 24 h before the target, which the cutoff already bounds; if one is
    missing, the latest forecast of that hour stands in.
    """
    hours, cut = _utc(ts.floor("h")), _utc(cutoff)
    cells = np.asarray(cells, dtype=object).astype(str)
    hi = _latest_issued(weather, "forecast", "heat_index_c", cells, hours, cut)
    rain = _latest_issued(weather, "forecast", "precipitation_mm", cells, hours, cut)
    before = hours - np.timedelta64(1, "D")
    observed = _latest_issued(weather, "archive", "heat_index_c", cells, before, cut)
    yesterday = np.where(np.isnan(observed), _latest_issued(weather, "forecast", "heat_index_c", cells, before, cut), observed)
    return {"hi_fcst_c": hi, "hi_fcst_minus_lag1d_c": hi - yesterday, "rain_fcst_mm": rain}


def issue_cutoff(ts) -> pd.DatetimeIndex:
    """00:00 Manila of each time's day: a day scored at 00:00 reads forecasts issued by then."""
    return pd.DatetimeIndex(pd.to_datetime(ts, utc=True)).tz_convert(LOCAL_TZ).normalize()


def add_weather_features(table: pd.DataFrame, weather: pd.DataFrame, transformers: pd.DataFrame) -> pd.DataFrame:
    """`WEATHER_FEATURES` for every (transformer, ts) row, as that day's 00:00 day-ahead run sees them."""
    cells = table["transformer_id"].astype(str).map(transformer_cells(transformers)).fillna("").to_numpy()
    ts = pd.DatetimeIndex(table["ts"])
    return table.assign(**weather_at(weather, cells, ts, issue_cutoff(ts)))


# --- EV exposure and clamp health (ADR 0007) ----------------------------------------------------

def stations_within(transformers: pd.DataFrame, stations: pd.DataFrame, radius_m: float = EV_STATION_RADIUS_M) -> np.ndarray:
    """Public EV chargers within `radius_m` of each transformer (haversine)."""
    phi_a = np.radians(transformers["lat"].to_numpy(float))[:, None]
    phi_b = np.radians(stations["lat"].to_numpy(float))[None, :]
    d_lambda = np.radians(stations["lon"].to_numpy(float))[None, :] - np.radians(transformers["lon"].to_numpy(float))[:, None]
    h = np.sin((phi_b - phi_a) / 2) ** 2 + np.cos(phi_a) * np.cos(phi_b) * np.sin(d_lambda / 2) ** 2
    distance = 2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(np.clip(h, 0.0, 1.0)))
    return (distance <= radius_m).sum(axis=1)


def evening_step_kw(history: pd.DataFrame, as_of: pd.Timestamp) -> pd.Series:
    """Per transformer: mean kW 20:00 to 24:00 over the 7 days before `as_of`, minus days 8 to 28.

    A plain stand-in for the `ruptures` change point in the SPEC: evening load the weeks before
    did not have, as when homes start charging EVs.
    """
    local = pd.DatetimeIndex(pd.to_datetime(history["ts"], utc=True)).tz_convert(LOCAL_TZ)
    as_of = pd.Timestamp(as_of).tz_convert(LOCAL_TZ)
    evening = np.asarray(local.hour >= EVENING_START_HOUR)
    recent = evening & np.asarray(local >= as_of - pd.Timedelta(days=7)) & np.asarray(local < as_of)
    earlier = evening & np.asarray(local >= as_of - pd.Timedelta(days=28)) & np.asarray(local < as_of - pd.Timedelta(days=7))
    ids, kw = history["transformer_id"].astype(str), history["transformer_kw"].astype(np.float64)
    return kw[recent].groupby(ids[recent]).mean().sub(kw[earlier].groupby(ids[earlier]).mean())


def reporting_share(history: pd.DataFrame, homes: pd.Series, as_of: pd.Timestamp) -> pd.Series:
    """Per transformer: mean homes reporting over the 24 h before `as_of`, over all its homes."""
    ts = pd.DatetimeIndex(pd.to_datetime(history["ts"], utc=True))
    as_of = pd.Timestamp(as_of).tz_convert("UTC")
    last_day = np.asarray(ts >= as_of - pd.Timedelta(days=1)) & np.asarray(ts < as_of)
    ids = history["transformer_id"].astype(str)
    reporting = history["homes_reporting"].astype(np.float64)[last_day].groupby(ids[last_day]).mean()
    return reporting / homes.reindex(reporting.index).astype(np.float64)


def risk_features_weather_ev(forecast: pd.DataFrame, transformers: pd.DataFrame, weather: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    """`risk_features` plus peak forecast heat index, evening step, chargers nearby and reporting share.

    `forecast` is one day's 24 h forecast from 00:00 (`kw_pred`), `history` the load before it,
    and `transformers` carries `ev_stations_within` (from `stations_within`).
    """
    base = risk_features(forecast, transformers)
    as_of = forecast["ts"].min()
    ids = base["transformer_id"].astype(str)
    cells = ids.map(transformer_cells(transformers)).fillna("").to_numpy()
    ts = pd.DatetimeIndex(np.sort(forecast["ts"].unique()))
    queries = len(ts) * len(cells)
    found = weather_at(weather, np.tile(cells, len(ts)), pd.DatetimeIndex(np.repeat(ts, len(cells))), issue_cutoff([as_of] * queries))
    heat = found["hi_fcst_c"].reshape(len(ts), len(cells)).T  # (transformers, steps)
    info = transformers.assign(transformer_id=transformers["transformer_id"].astype(str)).set_index("transformer_id")
    return base.assign(
        heat_index_max_c=np.fmax.reduce(heat, axis=1),
        ev_evening_step_kw=evening_step_kw(history, as_of).reindex(ids).to_numpy(dtype=np.float64),
        ev_stations_within=info["ev_stations_within"].reindex(ids).to_numpy(dtype=np.float64),
        reporting_pct=reporting_share(history, info["homes"], as_of).reindex(ids).to_numpy(dtype=np.float64),
    )
