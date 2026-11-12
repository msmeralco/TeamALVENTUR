"""Score the latest load interval once and store it; a failure is recorded and re-raised."""

from __future__ import annotations

import logging
import uuid

from silip.scoring.domain import Clock, RunResult
from silip.shared.readings.domain import DataSource
from silip.shared.scores.domain import DuplicateRunError, ScoreRun, ScoreStore
from silip.shared.scores.service import score_window

logger = logging.getLogger(__name__)


def _inputs_simulated(source: DataSource) -> bool:
    """Label a failed run like its inputs; when they cannot be read, assume simulated."""
    try:
        return bool(source.transformers()["is_simulated"].any())
    except Exception:  # noqa: BLE001 - labeling must not mask the original failure
        return True


def run_once(
    source: DataSource, store: ScoreStore, forecaster: str, risk_scorer: str, clock: Clock
) -> RunResult:
    """Idempotent per 15-minute data interval and strategy pair."""
    latest = source.latest_load_ts()
    if latest is None:
        logger.info("no load data yet; nothing to score")
        return RunResult("skipped", None, 0)
    as_of = latest.to_pydatetime()
    if store.has_complete_run(as_of, forecaster, risk_scorer):
        logger.info("interval %s already scored; skipping", as_of.isoformat())
        return RunResult("skipped", None, 0)
    run_id, started_at = str(uuid.uuid4()), clock()
    try:
        scored = score_window(source, as_of, forecaster, risk_scorer)
        run = ScoreRun(
            run_id=run_id,
            as_of=as_of,
            started_at=started_at,
            finished_at=clock(),
            forecaster=forecaster,
            risk_scorer=risk_scorer,
            transformers=len(scored.scores),
            is_simulated=any(score.is_simulated for score in scored.scores),
        )
        store.write_run(run, scored.scores, scored.forecast)
    except DuplicateRunError:
        logger.info("interval %s scored by a parallel run; skipping", as_of.isoformat())
        return RunResult("skipped", None, 0)
    except Exception as error:
        failed = ScoreRun(
            run_id,
            as_of,
            started_at,
            clock(),
            forecaster,
            risk_scorer,
            0,
            is_simulated=_inputs_simulated(source),
        )
        store.write_failed(failed, type(error).__name__)
        raise
    return RunResult("complete", run_id, run.transformers)
