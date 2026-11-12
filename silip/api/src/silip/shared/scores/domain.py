"""The ScoreStore port and the shapes of one stored scoring run.

Transformer totals only: a run holds risk per transformer and its 24 h forecast, never a sin_hash.
forecast columns: transformer_id, ts, kw_pred, is_simulated
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import pandas as pd

from silip_ml.risk.domain import RiskOutput

# Load history read per run. [VERIFY] design choice: the forecasters need 7 days + 1 step to
# predict, and the risk model needs more past days than that to fit.
SCORING_WINDOW = pd.Timedelta(days=14)


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


@dataclass(frozen=True)
class Scored:
    """Risk per transformer plus the forecast behind it (one `score_window` result)."""

    scores: tuple[RiskOutput, ...]
    forecast: pd.DataFrame


@dataclass(frozen=True)
class StoredRun:
    """The latest complete run, as the API reads it."""

    run: ScoreRun
    scores: tuple[RiskOutput, ...]
    forecast: pd.DataFrame


class ScoreStore(Protocol):
    """Insert-only store of scoring runs."""

    def has_complete_run(self, as_of: datetime, forecaster: str, risk_scorer: str) -> bool: ...

    def write_run(
        self, run: ScoreRun, scores: Sequence[RiskOutput], forecast: pd.DataFrame
    ) -> None:
        """Store a complete run with all its scores and forecast, atomically.

        Raises:
            DuplicateRunError: if a complete run for the same interval and strategies exists.
        """
        ...

    def write_failed(self, run: ScoreRun, error_class: str) -> None: ...

    def latest_run(self) -> StoredRun | None:
        """The complete run for the newest data interval, or None if there is none yet."""
        ...
