"""Decision rules for the engineer dashboard: the recommended action, clamp targets, and the
measured inputs behind them. Pure: values and frames in, values out.

Every threshold below decides what an engineer is told to do. None has a published source yet;
each is a design default to be set with Meralco engineers. [VERIFY]
"""

from __future__ import annotations

import math
from collections.abc import Hashable, Mapping
from datetime import datetime
from typing import Any, get_args

import numpy as np
import pandas as pd
from pydantic import BaseModel

from silip.shared.scores.domain import Action, ClampHealth, Driver, WeatherStatus
from silip_ml.features import evening_step_kw as ml_evening_step_kw
from silip_ml.readings.domain import load_pct
from silip_ml.risk.domain import WATCH_LOAD_PCT, Tier

# Below this share of homes reporting, the load estimate is too thin to send a crew on. [VERIFY]
MIN_TRUST_REPORTING = 0.5
# Clamp coverage to aim for when adding clamps. [VERIFY]
TARGET_COVERAGE = 0.6
# More than this share of installed clamps offline: fix them before trusting the estimate. [VERIFY]
CLAMP_OFFLINE_SHARE = 0.2
# Elevated (Watch or Critical level) on at least this many of the last 7 days: plan an upgrade.
# [VERIFY] Counted on measured daily peaks, not runs: runs are every 15 minutes (ADR 0002), so
# "7 runs" would be under two hours of history.
UPGRADE_DAYS_OF_7 = 3
UPGRADE_LOOKBACK_DAYS = 7
# Evening step above this suggests new EV charging worth an upgrade review. About one home
# charger (3.3 to 7.4 kW in the simulator recipe, silip-domain). [VERIFY]
EV_STEP_KW = 5.0
# Load read per run: the ADR 0007 evening step compares the last 7 days with days 8 to 28.
HISTORY_WINDOW = pd.Timedelta(days=28)
LOCAL_TZ = "Asia/Manila"
ACTIONS: tuple[Action, ...] = get_args(Action)
TIERS: tuple[Tier, ...] = get_args(Tier)


class WeatherSummary(BaseModel):
    """The forecast behind the view and its hottest hour ahead."""

    issued_at: datetime | None
    status: WeatherStatus
    source: str
    heat_index_max_c: float | None
    max_at: datetime | None


class ClampSummary(BaseModel):
    installed: int
    online: int


class ModelSummary(BaseModel):
    """Strategies used; `kept` is the backtest verdict (null for baselines)."""

    forecaster: str | None
    risk_scorer: str | None
    kept: bool | None


class DashboardSummary(BaseModel):
    """The summary row: as-of time, tiers, actions, weather freshness, clamps and model."""

    as_of: datetime
    scored_at: datetime
    tiers: dict[str, int]
    actions: dict[str, int]
    weather: WeatherSummary
    clamps: ClampSummary
    model: ModelSummary
    is_simulated: bool


def count(values: list[str], names: tuple[str, ...]) -> dict[str, int]:
    """Counts per name, zero included, in `names` order."""
    return {name: values.count(name) for name in names}


def recommend_action(
    tier: Tier,
    reporting_pct: float,
    offline_share: float,
    open_outage: bool,
    elevated_days: int,
    ev_evening_step_kw: float | None,
) -> Action:
    """The rules table, first match wins.

    1. Inspect before peak: Critical, enough homes reporting to trust it, and no open outage
       (a crew is already there).
    2. Fix clamps: too many installed clamps offline. Checked before Add clamps, because fixing
       a dead clamp restores coverage more cheaply than installing a new one.
    3. Add clamps: Watch or Critical on too few homes reporting to trust the estimate.
    4. Plan upgrade: elevated on UPGRADE_DAYS_OF_7 of the last 7 days, or a large evening step.
    5. Monitor.
    No "Rebalance": there is no per-phase data.
    """
    elevated = tier in ("Watch", "Critical")
    if tier == "Critical" and reporting_pct >= MIN_TRUST_REPORTING and not open_outage:
        return "Inspect before peak"
    if offline_share > CLAMP_OFFLINE_SHARE:
        return "Fix clamps"
    if elevated and reporting_pct < MIN_TRUST_REPORTING:
        return "Add clamps"
    if elevated_days >= UPGRADE_DAYS_OF_7 or (
        ev_evening_step_kw is not None and ev_evening_step_kw > EV_STEP_KW
    ):
        return "Plan upgrade"
    return "Monitor"


def clamps_to_target(homes: int, clamps_online: int) -> int:
    """More clamps (online) needed to reach TARGET_COVERAGE of the transformer's homes."""
    return max(0, math.ceil(TARGET_COVERAGE * homes) - clamps_online)


def clamp_health(homes: int, clamps_installed: int, clamps_online: int) -> ClampHealth:
    """A home reports when its clamp is online (one clamp per opted-in home)."""
    homes = max(int(homes), 0)
    online = min(int(clamps_online), int(clamps_installed))
    reporting = min(online, homes)
    return ClampHealth(
        homes=homes,
        clamps_installed=int(clamps_installed),
        clamps_online=online,
        homes_reporting=reporting,
        reporting_pct=reporting / homes if homes else 0.0,
    )


def offline_share(health: ClampHealth) -> float:
    if health.clamps_installed == 0:
        return 0.0
    return (health.clamps_installed - health.clamps_online) / health.clamps_installed


def open_outage_ids(outages: pd.DataFrame, as_of: pd.Timestamp) -> set[str]:
    """Transformers with an outage started by `as_of` and not yet restored at `as_of`."""
    if outages.empty:
        return set()
    started = outages["start_ts"] <= as_of
    ends = outages["start_ts"] + pd.to_timedelta(outages["duration_min"], unit="min")
    still_open = ends.isna() | (ends > as_of)
    return set(outages.loc[started & still_open, "transformer_id"].astype(str))


def _local(ts: pd.Series) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(pd.to_datetime(ts, utc=True)).tz_convert(LOCAL_TZ)


def evening_step_kw(history: pd.DataFrame, as_of: pd.Timestamp) -> dict[str, float]:
    """ADR 0007 evening step per transformer (`silip_ml.features.evening_step_kw`, the risk
    feature itself). A transformer without readings in both windows has no step (left out)."""
    if history.empty:
        return {}
    ids = history["transformer_id"].astype(str).unique()
    steps = ml_evening_step_kw(history, ids, pd.Timestamp(as_of))
    return {str(t): float(v) for t, v in zip(ids, steps, strict=True) if not np.isnan(v)}


def elevated_days(
    history: pd.DataFrame, transformers: pd.DataFrame, as_of: pd.Timestamp
) -> dict[str, int]:
    """Days of the last 7 (Manila) whose measured peak reached the Watch level."""
    if history.empty:
        return {}
    end = pd.Timestamp(as_of)
    recent = history[history["ts"] > end - pd.Timedelta(days=UPGRADE_LOOKBACK_DAYS)]
    rated = transformers.set_index("transformer_id")["rated_kva"]
    pct = load_pct(
        recent["transformer_kw"].to_numpy(float),
        recent["transformer_id"].map(rated).to_numpy(float),
    )
    days = _local(recent["ts"]).normalize()
    peaks = pd.DataFrame(
        {"transformer_id": recent["transformer_id"].astype(str).to_numpy(), "day": days, "pct": pct}
    )
    daily = peaks.groupby(["transformer_id", "day"])["pct"].max()
    counts = (daily >= WATCH_LOAD_PCT).groupby(level="transformer_id").sum()
    return {str(k): int(v) for k, v in counts.items()}


def heat_peak(
    weather: pd.DataFrame, cell: str, start: pd.Timestamp, end: pd.Timestamp
) -> tuple[float, pd.Timestamp] | None:
    """Highest forecast heat index in `cell` for hours in (start, end], and when."""
    if weather.empty:
        return None
    rows = weather[(weather["cell_id"] == cell) & (weather["ts"] > start) & (weather["ts"] <= end)]
    rows = rows.dropna(subset=["heat_index_c"])
    if rows.empty:
        return None
    top = max(rows.to_dict("records"), key=lambda row: row["heat_index_c"])
    return float(top["heat_index_c"]), pd.Timestamp(top["ts"])


def by_transformer(frame: pd.DataFrame) -> dict[str, dict[Hashable, Any]]:
    """Records keyed by transformer_id."""
    return {str(row["transformer_id"]): row for row in frame.to_dict("records")}


# Per model input: (unit, scale to that unit, where the value comes from). "weather" is replaced
# by the forecast's provider label.
FEATURE_INFO: dict[str, tuple[str, float, str]] = {
    "peak_load_pct": ("% of rating", 100.0, "Forecast"),
    "mean_load_pct": ("% of rating", 100.0, "Forecast"),
    "hours_over_100": ("h", 1.0, "Forecast"),
    "hours_over_110": ("h", 1.0, "Forecast"),
    "hours_over_90": ("h", 1.0, "Forecast"),
    "coverage_pct": ("%", 100.0, "Clamps"),
    "reporting_pct": ("%", 100.0, "Clamps"),
    "rated_kva": ("kVA", 1.0, "Transformer"),
    "heat_index_max_c": ("°C", 1.0, "weather"),
    "ev_evening_step_kw": ("kW", 1.0, "Measured load"),
    "ev_stations_within": ("stations", 1.0, "DOE stations"),
}


def driver(
    feature: str,
    label: str,
    row: Mapping[Hashable, Any] | None,
    contribution: float | None,
    weather_source: str,
) -> Driver:
    """One driver: the feature's value from its `risk_features` row, in display units."""
    unit, scale, source = FEATURE_INFO.get(feature, (None, 1.0, "Model"))
    raw = None if row is None else row.get(feature)
    value = None if raw is None or pd.isna(raw) else round(float(raw) * scale, 2)
    return Driver(
        feature=feature,
        label=label,
        value=value,
        unit=unit,
        contribution=contribution,
        source=weather_source if source == "weather" else source,
    )


def rule_drivers(row: Mapping[Hashable, Any], reasons: list[str]) -> list[Driver]:
    """Drivers from the rules scorer's reasons (`silip_ml.risk.domain.reasons_for`): the same
    sentences, in its order, with the value behind each. No model, so no contribution."""
    features = ["peak_load_pct"]
    if row["hours_over_100"] > 0:
        features.append("hours_over_100")
    features.append("coverage_pct")
    return [
        driver(feature, label, row, None, "")
        for feature, label in zip(features, reasons, strict=False)
    ]
