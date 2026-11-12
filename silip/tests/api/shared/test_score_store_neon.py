"""NeonScoreStore against a real database: one transaction per run, one complete run per interval.

Runs only when DATABASE_URL or DATABASE_POOLER_URL is set, after the owner applied db/schema.sql.
Rows are insert-only and stay behind, so they use a year-2000 interval (never the latest run) and
a strategy name no real run uses.
"""

import os
import uuid
from datetime import UTC, datetime, timedelta

import pandas as pd
import psycopg
import pytest

from silip.shared.config import ApiSettings
from silip.shared.db import connect
from silip.shared.scores.adapters import NeonScoreStore
from silip.shared.scores.domain import DuplicateRunError, ScoreRun
from silip_ml.risk.domain import RiskOutput

NEON_URL_SET = bool(os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_POOLER_URL"))
TEST_STRATEGY = "contract-test"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not NEON_URL_SET, reason="needs DATABASE_URL"),
]


@pytest.fixture
def store_and_transformer() -> tuple[NeonScoreStore, str]:
    settings = ApiSettings()
    with connect(settings) as connection:
        row = connection.execute("SELECT transformer_id FROM transformer LIMIT 1").fetchone()
    assert row is not None, "transformer is empty; run python -m silip.shared.load_sim"
    return NeonScoreStore(lambda: connect(settings)), str(row[0])


def _run(as_of: datetime) -> ScoreRun:
    now = datetime.now(UTC)
    return ScoreRun(str(uuid.uuid4()), as_of, now, now, TEST_STRATEGY, TEST_STRATEGY, 1, True)


def _score(transformer_id: str) -> RiskOutput:
    return RiskOutput(
        transformer_id=transformer_id,
        tier="OK",
        reasons=["contract test"],
        confidence=0.5,
        peak_load_pct=0.5,
        coverage_pct=0.5,
        is_simulated=True,
    )


def _forecast(transformer_id: str, as_of: datetime) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "transformer_id": transformer_id,
            "ts": [as_of + timedelta(minutes=15), as_of + timedelta(minutes=30)],
            "kw_pred": [1.0, 2.0],
            "is_simulated": True,
        }
    )


def _unique_interval() -> datetime:
    return datetime(2000, 1, 1, tzinfo=UTC) + timedelta(minutes=15 * uuid.uuid4().int % 10**6)


def _stored_runs(run_id: str) -> int:
    with connect(ApiSettings()) as connection:
        row = connection.execute(
            "SELECT count(*) FROM score_run WHERE run_id = %(run_id)s", {"run_id": run_id}
        ).fetchone()
    return int(row[0]) if row else 0


def test_a_complete_run_is_stored_once_per_interval(store_and_transformer):
    store, transformer_id = store_and_transformer
    as_of = _unique_interval()
    run = _run(as_of)

    store.write_run(run, [_score(transformer_id)], _forecast(transformer_id, as_of))

    assert store.has_complete_run(as_of, TEST_STRATEGY, TEST_STRATEGY)
    with pytest.raises(DuplicateRunError):
        store.write_run(_run(as_of), [_score(transformer_id)], _forecast(transformer_id, as_of))


def test_a_run_that_fails_midway_leaves_no_rows(store_and_transformer):
    store, transformer_id = store_and_transformer
    as_of = _unique_interval()
    run = _run(as_of)
    bad_forecast = _forecast("NO-SUCH-TRANSFORMER", as_of)  # breaks the foreign key in COPY

    with pytest.raises(psycopg.Error):
        store.write_run(run, [_score(transformer_id)], bad_forecast)

    assert _stored_runs(run.run_id) == 0
    assert not store.has_complete_run(as_of, TEST_STRATEGY, TEST_STRATEGY)
