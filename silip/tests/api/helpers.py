"""Test helpers: a fake Cognito decoder, auth headers, a fake score store and a clock."""

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from silip.shared.auth.domain import AuthenticationError
from silip.shared.scores.domain import DuplicateRunError, ScoreRun, StoredRun
from silip_ml.risk.domain import RiskOutput

CLIENT_ID = "test-client"
GROUPS = {"engineer-token": ["engineers"], "household-token": ["households"], "nogroup-token": []}


class FakeDecoder:
    """Maps a few fixed tokens to claims; anything else is invalid."""

    def decode(self, token: str) -> Mapping[str, Any]:
        if token not in GROUPS:
            raise AuthenticationError("unknown test token")
        return {
            "token_use": "access",
            "client_id": CLIENT_ID,
            "sub": f"sub-{token}",
            "username": token.removesuffix("-token"),
            "cognito:groups": GROUPS[token],
        }


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class FakeScoreStore:
    """In-memory ScoreStore with the Neon store's rules: insert-only, latest complete run wins."""

    def __init__(self) -> None:
        self.complete: list[StoredRun] = []
        self.failed: list[tuple[ScoreRun, str]] = []

    def has_complete_run(self, as_of: datetime, forecaster: str, risk_scorer: str) -> bool:
        return any(
            (s.run.as_of, s.run.forecaster, s.run.risk_scorer) == (as_of, forecaster, risk_scorer)
            for s in self.complete
        )

    def write_run(
        self, run: ScoreRun, scores: Sequence[RiskOutput], forecast: pd.DataFrame
    ) -> None:
        if FakeScoreStore.has_complete_run(self, run.as_of, run.forecaster, run.risk_scorer):
            raise DuplicateRunError(run.as_of.isoformat())  # the unique index on score_run
        self.complete.append(StoredRun(run, tuple(scores), forecast.copy()))

    def write_failed(self, run: ScoreRun, error_class: str) -> None:
        self.failed.append((run, error_class))

    def latest_run(self) -> StoredRun | None:
        return max(self.complete, key=lambda s: (s.run.as_of, s.run.finished_at), default=None)


class StepClock:
    """A clock that moves forward one second per call, from a fixed start."""

    def __init__(self, start: datetime) -> None:
        self.now = start

    def __call__(self) -> datetime:
        self.now += timedelta(seconds=1)
        return self.now
