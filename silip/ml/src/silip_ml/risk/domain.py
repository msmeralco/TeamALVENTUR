"""The RiskScorer port, the risk output shape, and the shared window features."""

from __future__ import annotations

from collections.abc import Callable, Hashable, Mapping
from datetime import datetime
from typing import Any, Literal, Protocol, Self

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from silip_ml.ev import EV_STATION_RADIUS_M
from silip_ml.features import WeatherInput, longest_run
from silip_ml.readings.domain import STEPS_PER_HOUR

Tier = Literal["OK", "Watch", "Critical"]
Row = Mapping[Hashable, Any]  # one record from DataFrame.to_dict("records")

# Baseline rule from docs/SPEC.md#models: load >100% for 2 h.
CRITICAL_LOAD_PCT, CRITICAL_MIN_STEPS = 1.0, 2 * STEPS_PER_HOUR
# Watch threshold is a placeholder until engineers set it. [VERIFY]
WATCH_LOAD_PCT = 0.9
# Ground truth for backtests (silip-domain trip rule): load >110% for 3+ h.
TRIP_LOAD_PCT, TRIP_MIN_STEPS = 1.10, 3 * STEPS_PER_HOUR
MAX_REASONS = 3
# Below this share of homes reporting, a reason says the estimate is less certain. [VERIFY]
LOW_REPORTING_PCT = 0.5


class Driver(BaseModel):
    """One model input that pushed the score up, with its contribution (log-odds) and sentence."""

    feature: str
    contribution: float
    text: str


class RiskOutput(BaseModel):
    """Risk for one transformer over the forecast window."""

    transformer_id: str
    tier: Tier
    reasons: list[str] = Field(max_length=MAX_REASONS)
    confidence: float = Field(
        ge=0, le=1, description="Share of homes reporting (clamp health); coverage when unknown"
    )
    peak_load_pct: float
    coverage_pct: float = Field(ge=0, le=1)
    is_simulated: bool
    peak_ts: datetime | None = None
    drivers: list[Driver] = Field(default_factory=list, max_length=MAX_REASONS)


class RiskScorer(Protocol):
    """Turns a load forecast into a tier, reasons and confidence per transformer.

    `fit` is a no-op kept for callers written for trained-on-request models; remove it once no
    caller uses it. Trained scorers load an exported artifact.
    """

    def fit(self, load: pd.DataFrame, transformers: pd.DataFrame) -> Self: ...

    def score(
        self,
        forecast: pd.DataFrame,
        transformers: pd.DataFrame,
        weather: WeatherInput | None = None,
        history: pd.DataFrame | None = None,
    ) -> list[RiskOutput]:
        """`weather` and `history` (load before the window) feed the features that need them."""
        ...


def is_trip(pct: np.ndarray) -> bool:
    """Ground-truth failure: load above `TRIP_LOAD_PCT` for `TRIP_MIN_STEPS` in a row."""
    return bool(longest_run(pct > TRIP_LOAD_PCT)[0] >= TRIP_MIN_STEPS)


def reasons_for(row: Row) -> list[str]:
    """Plain-language reasons, most important first. `row` is one `risk_features` record."""
    reasons = [f"Peak forecast {row['peak_load_pct']:.0%} of rating at {row['peak_ts']:%H:%M}"]
    if row["hours_over_100"] > 0:
        reasons.append(f"Above 100% of rating for {row['hours_over_100']:.1f} h in a row")
    reasons.append(f"{row['coverage_pct']:.0%} of homes metered")
    return reasons[:MAX_REASONS]


def _known(value: Any) -> bool:
    return value is not None and bool(pd.notna(value))


def _evening_step(row: Row) -> str | None:
    step = row["ev_evening_step_kw"]
    if step <= 0:
        return None
    return f"Evening load up {step:.1f} kW vs the 3 weeks before; EV charging likely"


def _chargers(row: Row) -> str | None:
    count = int(row["ev_stations_within"])
    if count == 0:
        return None
    noun = "charger" if count == 1 else "chargers"
    return f"{count} public EV {noun} within {EV_STATION_RADIUS_M / 1000:g} km (DOE)"


def _reporting(row: Row) -> str:
    share = row["reporting_pct"]
    if share < LOW_REPORTING_PCT:
        return f"Only {share:.0%} of homes reporting; estimate less certain"
    return f"{share:.0%} of homes reporting"


# One sentence per model input; None means the value does not explain a higher risk.
REASON_TEMPLATES: dict[str, Callable[[Row], str | None]] = {
    "peak_load_pct": lambda r: (
        f"Peak forecast {r['peak_load_pct']:.0%} of rating at {r['peak_ts']:%H:%M}"
    ),
    "mean_load_pct": lambda r: f"Forecast averages {r['mean_load_pct']:.0%} of rating over the day",
    "hours_over_100": lambda r: (
        f"Above 100% of rating for {r['hours_over_100']:.1f} h in a row"
        if r["hours_over_100"] > 0
        else None
    ),
    "hours_over_110": lambda r: (
        f"Above 110% of rating for {r['hours_over_110']:.1f} h in a row"
        if r["hours_over_110"] > 0
        else None
    ),
    "hours_over_90": lambda r: (
        f"{r['hours_over_90']:.1f} h above 90% of rating" if r["hours_over_90"] > 0 else None
    ),
    "coverage_pct": lambda r: f"{r['coverage_pct']:.0%} of homes metered",
    "rated_kva": lambda r: f"Rated {r['rated_kva']:g} kVA",
    "heat_index_max_c": lambda r: (
        f"Forecast heat index {r['heat_index_max_c']:.0f} °C at {r['heat_index_max_ts']:%H:%M}"
        f" ({r['weather_source']})"
    ),
    "ev_evening_step_kw": _evening_step,
    "ev_stations_within": _chargers,
    "reporting_pct": _reporting,
}


def contribution_drivers(row: Row, contributions: Mapping[str, float]) -> list[Driver]:
    """Up to 3 inputs with the largest positive contributions, written as sentences.

    `contributions` are LightGBM `pred_contrib` values per feature (the bias term excluded).
    Inputs that are missing or whose value does not explain a higher risk are skipped.
    """
    drivers = []
    for feature, value in sorted(contributions.items(), key=lambda item: -item[1]):
        if value <= 0 or len(drivers) == MAX_REASONS:
            break
        template = REASON_TEMPLATES.get(feature)
        if template is None or not _known(row.get(feature)):
            continue
        text = template(row)
        if text is not None:
            drivers.append(Driver(feature=feature, contribution=float(value), text=text))
    return drivers


def confidence_for(row: Row) -> float:
    """Share of homes reporting (clamp health); metering coverage when it is unknown."""
    share = row.get("reporting_pct")
    value = float(share) if share is not None and _known(share) else float(row["coverage_pct"])
    return min(max(value, 0.0), 1.0)


def risk_output(row: Row, tier: Tier, drivers: list[Driver] | None = None) -> RiskOutput:
    """Build the output for one `risk_features` record.

    Reasons are the drivers' sentences when there are any, else the rule reasons.
    """
    drivers = drivers or []
    peak_ts = row.get("peak_ts")
    return RiskOutput(
        transformer_id=row["transformer_id"],
        tier=tier,
        reasons=[d.text for d in drivers] or reasons_for(row),
        confidence=confidence_for(row),
        peak_load_pct=row["peak_load_pct"],
        coverage_pct=row["coverage_pct"],
        is_simulated=row["is_simulated"],
        peak_ts=pd.Timestamp(peak_ts).to_pydatetime()
        if peak_ts is not None and _known(peak_ts)
        else None,
        drivers=drivers,
    )
