"""Inference features, built for every transformer at once.

Definitions match `notebooks/_features.py`, where the models are trained. The export notebook
writes a parity sample to `models/<task>/<name>/parity/`; `tests/ml/test_parity.py` fails if these
functions stop reproducing it. Change a feature in both places, then re-export.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from silip_ml.readings.domain import ASSUMED_POWER_FACTOR, STEPS_PER_DAY, STEPS_PER_HOUR
from silip_ml.weather import cell_id

STEP = pd.Timedelta("15min")
LOCAL_TZ = "Asia/Manila"  # weather forecasts are issued at 00:00 Manila time
WEATHER_LOAD_FEATURES = ("hi_fcst_c", "hi_fcst_minus_lag1d_c", "rain_fcst_mm")
EVENING_START_HOUR = 20  # EV charging starts from 8 PM in the simulator (silip-domain)


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


@dataclass(frozen=True)
class WeatherInput:
    """Hourly weather rows and the weather cell of each transformer.

    `rows` has the `weather_forecast_hourly.csv` / `weather_hourly` columns: `issued_at, ts,
    cell_id, heat_index_c, precipitation_mm, kind (archive|forecast), is_simulated`.
    """

    rows: pd.DataFrame
    cells: Mapping[str, str]  # transformer_id -> cell_id

    @property
    def source(self) -> str:
        """Label for reasons: simulated rows never say Open-Meteo."""
        simulated = "is_simulated" not in self.rows or self.rows["is_simulated"].astype(bool).any()
        return "Simulated" if simulated else "Open-Meteo"


def weather_input(rows: pd.DataFrame, transformers: pd.DataFrame) -> WeatherInput:
    """Map each transformer to its weather cell (`silip_ml.weather.cell_id`)."""
    located = transformers.dropna(subset=["lat", "lon"])
    cells = {
        str(t): cell_id(float(lat), float(lon))
        for t, lat, lon in zip(
            located["transformer_id"], located["lat"], located["lon"], strict=True
        )
    }
    return WeatherInput(rows, cells)


def _utc(values: pd.Series | pd.DatetimeIndex) -> np.ndarray:
    """Naive UTC datetime64[ns], so frames from CSV (+08:00) and Neon (Asia/Manila) compare."""
    return (
        pd.DatetimeIndex(pd.to_datetime(values, utc=True))
        .tz_localize(None)
        .as_unit("ns")
        .to_numpy()
    )


def _latest_issued(
    rows: pd.DataFrame,
    kind: str,
    column: str,
    cells: np.ndarray,
    hours: np.ndarray,
    cutoff: np.ndarray,
) -> np.ndarray:
    """`column` of the latest `kind` row issued at or before `cutoff`, per query; NaN if none."""
    right = rows.loc[rows["kind"] == kind, ["cell_id", "ts", "issued_at", column]]
    right = pd.DataFrame(
        {
            "cell_id": right["cell_id"].astype(str).to_numpy(),
            "ts": _utc(right["ts"]),
            "issued_at": _utc(right["issued_at"]),
            "value": right[column].to_numpy(dtype=np.float64),
        }
    ).sort_values("issued_at", kind="stable")
    left = pd.DataFrame(
        {"cell_id": cells, "ts": hours, "cutoff": cutoff, "i": np.arange(len(cells))}
    ).sort_values("cutoff", kind="stable")
    merged = pd.merge_asof(
        left, right, left_on="cutoff", right_on="issued_at", by=["cell_id", "ts"]
    )
    return merged.sort_values("i")["value"].to_numpy(dtype=np.float64)


def weather_at(
    weather: pd.DataFrame, cells: np.ndarray, ts: pd.DatetimeIndex, cutoff: pd.DatetimeIndex
) -> dict[str, np.ndarray]:
    """Weather features for target times `ts` in cells `cells`, known at `cutoff` (one per query).

    Only rows issued at or before the cutoff are read. The forecast is the latest `forecast` row
    for the target hour; the reference 24 h earlier is the observed (`archive`) hour, else the
    latest forecast of it. Archive rows are never read for hours after the cutoff.
    """
    hours = _utc(ts.floor("h"))
    cut = _utc(cutoff)
    cells = np.asarray(cells, dtype=object).astype(str)
    hi = _latest_issued(weather, "forecast", "heat_index_c", cells, hours, cut)
    rain = _latest_issued(weather, "forecast", "precipitation_mm", cells, hours, cut)
    before = hours - np.timedelta64(1, "D")
    observed = _latest_issued(weather, "archive", "heat_index_c", cells, before, cut)
    forecast_before = _latest_issued(weather, "forecast", "heat_index_c", cells, before, cut)
    yesterday = np.where(np.isnan(observed), forecast_before, observed)
    return {"hi_fcst_c": hi, "hi_fcst_minus_lag1d_c": hi - yesterday, "rain_fcst_mm": rain}


def issue_cutoff(as_of: pd.Timestamp) -> pd.Timestamp:
    """The run day's 00:00 in Manila: forecasts used at `as_of` were issued at or before it."""
    return pd.Timestamp(as_of).tz_convert(LOCAL_TZ).normalize()


def _weather_columns(
    transformer_ids: np.ndarray,
    ts: pd.DatetimeIndex,
    as_of: pd.Timestamp,
    weather: WeatherInput | None,
) -> dict[str, np.ndarray]:
    """Weather features as (times, transformers), known when scored at `as_of`; NaN without
    weather or a known cell."""
    shape = (len(ts), len(transformer_ids))
    if weather is None:
        return {name: np.full(shape, np.nan) for name in WEATHER_LOAD_FEATURES}
    cells = np.array([weather.cells.get(str(t), "") for t in transformer_ids], dtype=object)
    found = weather_at(
        weather.rows,
        np.tile(cells, len(ts)),
        pd.DatetimeIndex(np.repeat(ts, len(cells))),
        pd.DatetimeIndex([issue_cutoff(as_of)] * (len(ts) * len(cells))),
    )
    return {name: values.reshape(shape) for name, values in found.items()}


def load_features(
    grid: Grid,
    rows: np.ndarray,
    features: Sequence[str],
    holidays: Sequence[str],
    weather: WeatherInput | None = None,
) -> np.ndarray:
    """Feature matrix for `rows` of `grid`, ordered transformer by transformer, then by row.

    Weather features read forecasts issued by 00:00 (Manila) of the day the history ends; without
    `weather` they are NaN, which LightGBM routes down its missing-value branch.

    Raises:
        UnknownFeatureError: if `features` names something not defined here.
    """
    ts = grid.ts(rows)
    as_of = grid.ts(np.array([grid.steps]))[0]  # scored when the history ends
    weather_columns = (
        _weather_columns(grid.transformer_ids, ts, as_of, weather)
        if any(name in WEATHER_LOAD_FEATURES for name in features)
        else {}
    )
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
        elif name in weather_columns:
            column = weather_columns[name]
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
    "heat_index_max_c",
    "ev_evening_step_kw",
    "ev_stations_within",
    "reporting_pct",
]


def evening_step_kw(
    history: pd.DataFrame, transformer_ids: np.ndarray, as_of: pd.Timestamp
) -> np.ndarray:
    """Mean kW from 20:00 to 24:00 over the 7 days before `as_of`, minus days 8 to 28 before it.

    A plain stand-in for the `ruptures` change point in docs/SPEC.md: a step up in evening load
    that the weeks before did not have, as when homes start charging EVs. NaN without history.
    """
    local = pd.DatetimeIndex(pd.to_datetime(history["ts"], utc=True)).tz_convert(LOCAL_TZ)
    as_of = pd.Timestamp(as_of).tz_convert(LOCAL_TZ)
    evening = np.asarray(local.hour >= EVENING_START_HOUR)
    recent = evening & np.asarray(local >= as_of - pd.Timedelta(days=7)) & np.asarray(local < as_of)
    earlier = (
        evening
        & np.asarray(local >= as_of - pd.Timedelta(days=28))
        & np.asarray(local < as_of - pd.Timedelta(days=7))
    )
    ids = history["transformer_id"].astype(str)
    kw = history["transformer_kw"].astype(np.float64)
    last_week = kw[recent].groupby(ids[recent]).mean()
    weeks_before = kw[earlier].groupby(ids[earlier]).mean()
    step = last_week.sub(weeks_before)  # NaN unless both windows have readings
    return step.reindex(transformer_ids).to_numpy(dtype=np.float64)


def reporting_share(
    history: pd.DataFrame, info: pd.DataFrame, transformer_ids: np.ndarray, as_of: pd.Timestamp
) -> np.ndarray:
    """Homes reporting over the 24 h before `as_of`, as a share of all homes. NaN without data."""
    ts = pd.DatetimeIndex(pd.to_datetime(history["ts"], utc=True))
    as_of = pd.Timestamp(as_of).tz_convert("UTC")
    last_day = np.asarray(ts >= as_of - pd.Timedelta(days=1)) & np.asarray(ts < as_of)
    ids = history["transformer_id"].astype(str)
    reporting = (
        history["homes_reporting"].astype(np.float64)[last_day].groupby(ids[last_day]).mean()
    )
    homes = info["homes"].to_numpy(dtype=np.float64)
    return reporting.reindex(transformer_ids).to_numpy(dtype=np.float64) / homes


def risk_features(
    forecast: pd.DataFrame,
    kw_column: str,
    transformers: pd.DataFrame,
    weather: WeatherInput | None = None,
    history: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """One row per transformer from its forecast window, plus `peak_ts`, `heat_index_max_ts`,
    `weather_source` and `is_simulated`.

    `transformers` needs `transformer_id, rated_kva, coverage_pct, is_simulated`; `homes` and
    `ev_stations_within` (from `silip_ml.ev.stations_within`) are used when present. `history`
    is the load before the window (`transformer_kw`, `homes_reporting`). Features without their
    input are NaN. Transformers missing from `transformers` are dropped.
    """
    grid = to_grid(forecast, kw_column)
    info = transformers.assign(transformer_id=transformers["transformer_id"].astype(str))
    info = info.set_index("transformer_id").reindex(grid.transformer_ids)
    known = info["rated_kva"].notna().to_numpy()
    rated = info["rated_kva"].to_numpy(dtype=np.float64)
    # (transformers, steps), C-contiguous so each row's mean sums in the same order as the notebook's
    pct = np.ascontiguousarray(grid.values.T) / (rated[:, None] * ASSUMED_POWER_FACTOR)
    peak_step = np.nanargmax(np.where(np.isnan(pct), -np.inf, pct), axis=1)
    as_of = grid.start  # scored when the window starts
    heat = _weather_columns(grid.transformer_ids, grid.ts(np.arange(grid.steps)), as_of, weather)
    heat_index = np.ascontiguousarray(heat["hi_fcst_c"].T)  # (transformers, steps)
    heat_max = np.fmax.reduce(heat_index, axis=1)  # NaN only when the whole window is
    hot_step = np.argmax(np.where(np.isnan(heat_index), -np.inf, heat_index), axis=1)
    nan = np.full(len(grid.transformer_ids), np.nan)
    past = history if history is not None else pd.DataFrame()
    step = evening_step_kw(past, grid.transformer_ids, as_of) if not past.empty else nan
    reporting = (
        reporting_share(past, info, grid.transformer_ids, as_of)
        if not past.empty and "homes" in info and "homes_reporting" in past
        else nan
    )
    simulated = info["is_simulated"].fillna(True).astype(bool).to_numpy()
    if weather is not None:
        simulated = simulated | (weather.source == "Simulated")
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
            "heat_index_max_c": heat_max,
            "heat_index_max_ts": grid.ts(hot_step).where(~np.isnan(heat_max)),
            "ev_evening_step_kw": step,
            "ev_stations_within": info["ev_stations_within"].to_numpy(dtype=np.float64)
            if "ev_stations_within" in info
            else nan,
            "reporting_pct": reporting,
            "weather_source": weather.source if weather is not None else None,
            "is_simulated": simulated,
        }
    )
    return features[known].reset_index(drop=True)
