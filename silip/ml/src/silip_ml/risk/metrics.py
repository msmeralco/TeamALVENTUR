"""Risk metrics for the backtest: recall of real trips and false alarms."""

from __future__ import annotations

from dataclasses import dataclass

DAYS_PER_MONTH = 30


@dataclass(frozen=True)
class RiskCounts:
    """Counts over (transformer, day) windows. `flagged` means tier Critical."""

    trips: int = 0
    caught: int = 0
    false_alarms: int = 0
    windows: int = 0

    def add(self, flagged: bool, tripped: bool) -> RiskCounts:
        return RiskCounts(
            trips=self.trips + tripped,
            caught=self.caught + (flagged and tripped),
            false_alarms=self.false_alarms + (flagged and not tripped),
            windows=self.windows + 1,
        )

    @property
    def recall(self) -> float:
        return self.caught / self.trips if self.trips else float("nan")

    @property
    def false_alarms_per_transformer_month(self) -> float:
        return self.false_alarms / self.windows * DAYS_PER_MONTH if self.windows else float("nan")
