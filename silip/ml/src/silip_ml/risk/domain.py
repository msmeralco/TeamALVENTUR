"""The RiskScorer port, the risk output shape, and the shared window features."""

from __future__ import annotations

from collections.abc import Hashable, Mapping
from typing import Any, Literal, Protocol, Self

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from silip_ml.features import longest_run
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


class RiskOutput(BaseModel):
    """Risk for one transformer over the forecast window."""

    transformer_id: str
    tier: Tier
    reasons: list[str] = Field(max_length=MAX_REASONS)
    confidence: float = Field(ge=0, le=1, description="Tied to metering coverage")
    peak_load_pct: float
    coverage_pct: float = Field(ge=0, le=1)
    is_simulated: bool


class RiskScorer(Protocol):
    """Turns a load forecast into a tier, reasons and confidence per transformer.

    `fit` is a no-op kept for callers written for trained-on-request models; remove it once no
    caller uses it. Trained scorers load an exported artifact.
    """

    def fit(self, load: pd.DataFrame, transformers: pd.DataFrame) -> Self: ...

    def score(self, forecast: pd.DataFrame, transformers: pd.DataFrame) -> list[RiskOutput]: ...


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


def risk_output(row: Row, tier: Tier) -> RiskOutput:
    """Build the output for one `risk_features` record. Confidence equals metering coverage."""
    return RiskOutput(
        transformer_id=row["transformer_id"],
        tier=tier,
        reasons=reasons_for(row),
        confidence=row["coverage_pct"],
        peak_load_pct=row["peak_load_pct"],
        coverage_pct=row["coverage_pct"],
        is_simulated=row["is_simulated"],
    )
