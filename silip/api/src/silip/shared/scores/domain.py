"""The ScoreStore port and the shapes of one stored scoring run.

Transformer totals only: a run holds risk per transformer and its 24 h forecast, never a sin_hash.
forecast columns: transformer_id, ts, kw_pred, is_simulated
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Protocol

import pandas as pd
from pydantic import BaseModel, Field

from silip_ml.risk.domain import RiskOutput

# Load history read per run. [VERIFY] design choice: the forecasters need 7 days + 1 step to
# predict, and the risk model needs more past days than that to fit.
SCORING_WINDOW = pd.Timedelta(days=14)


# The rules-table action per transformer (silip.dashboard.domain decides it).
Action = Literal["Inspect before peak", "Add clamps", "Fix clamps", "Plan upgrade", "Monitor"]
WeatherStatus = Literal["fresh", "stale", "missing"]


class Driver(BaseModel):
    """One reason behind a score, as a feature and its value. `contribution` is the model's
    per-feature contribution (LightGBM `pred_contrib`); null when the rules scorer gave it."""

    feature: str
    label: str
    value: float | None = None
    unit: str | None = None
    contribution: float | None = None
    source: str


class ClampHealth(BaseModel):
    """Retrofit clamp counts for one transformer (or an area). Counts only, never a device."""

    homes: int
    clamps_installed: int
    clamps_online: int
    homes_reporting: int
    reporting_pct: float = Field(ge=0, le=1, description="homes_reporting / homes")


class ScoreDetail(BaseModel):
    """Dashboard fields stored beside a transformer's score. Transformer totals and counts only."""

    transformer_id: str
    peak_ts: datetime | None = None
    action: Action = "Monitor"
    drivers: list[Driver] = Field(default_factory=list)
    heat_index_max_c: float | None = None
    ev_evening_step_kw: float | None = None
    homes_reporting: int | None = None
    clamps_installed: int | None = None
    clamps_online: int | None = None


class DuplicateRunError(RuntimeError):
    """Another run already stored a complete run for this interval and strategy pair."""


@dataclass(frozen=True)
class ScoreRun:
    """One scoring run. `as_of` is the latest 15-minute load interval scored."""

    run_id: str
    as_of: datetime
    started_at: datetime
    finished_at: datetime
    forecaster: str
    risk_scorer: str
    transformers: int
    is_simulated: bool
    weather_issued_at: datetime | None = None
    weather_status: WeatherStatus | None = None


@dataclass(frozen=True)
class Scored:
    """Risk per transformer plus the forecast behind it (one `score_window` result).

    `features` holds the risk scorer's per-transformer inputs (`silip_ml.features.risk_features`);
    `history` is the load read for the window.
    """

    scores: tuple[RiskOutput, ...]
    forecast: pd.DataFrame
    features: pd.DataFrame = field(default_factory=pd.DataFrame)
    history: pd.DataFrame = field(default_factory=pd.DataFrame)


@dataclass(frozen=True)
class StoredRun:
    """The latest complete run, as the API reads it."""

    run: ScoreRun
    scores: tuple[RiskOutput, ...]
    forecast: pd.DataFrame
    details: tuple[ScoreDetail, ...] = ()


class ScoreStore(Protocol):
    """Insert-only store of scoring runs."""

    def has_complete_run(self, as_of: datetime, forecaster: str, risk_scorer: str) -> bool: ...

    def write_run(
        self,
        run: ScoreRun,
        scores: Sequence[RiskOutput],
        forecast: pd.DataFrame,
        details: Sequence[ScoreDetail] = (),
    ) -> None:
        """Store a complete run with all its scores, dashboard details and forecast, atomically.

        Raises:
            DuplicateRunError: if a complete run for the same interval and strategies exists.
        """
        ...

    def write_failed(self, run: ScoreRun, error_class: str) -> None: ...

    def latest_run(self) -> StoredRun | None:
        """The complete run for the newest data interval, or None if there is none yet."""
        ...
