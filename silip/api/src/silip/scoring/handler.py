"""Lambda entry point for the scheduled scoring job (EventBridge Scheduler)."""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from silip.scoring.service import run_once
from silip.shared.config import get_settings
from silip.shared.deps import get_data_source, get_score_store

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(UTC)


def handle(event: dict[str, Any], context: object) -> dict[str, Any]:
    """Score the latest interval. Returns {"status", "run_id", "transformers"}."""
    settings = get_settings()
    store = get_score_store(settings)
    if store is None:
        logger.warning("DATA_SOURCE=simulated has no score store; the API scores on request")
        return {"status": "skipped"}
    source = get_data_source(settings)
    result = run_once(source, store, settings.forecaster, settings.risk_scorer, utc_now)
    logger.info(
        "scoring %s: run %s, %d transformers", result.status, result.run_id, result.transformers
    )
    return asdict(result)
