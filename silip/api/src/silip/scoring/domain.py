"""What one scheduled scoring run reports."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from silip.shared.scores.domain import SCORING_WINDOW

__all__ = ["SCORING_WINDOW", "Clock", "RunResult"]

Clock = Callable[[], datetime]  # timezone-aware now(); injected so tests control time


@dataclass(frozen=True)
class RunResult:
    """`skipped` when there is no load yet or this interval already has a complete run."""

    status: Literal["complete", "skipped"]
    run_id: str | None
    transformers: int
