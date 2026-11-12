"""Lambda entry point for the IoT Core topic rule (`SELECT * FROM 'silip/v1/+/+/reading'`)."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from silip.ingest.adapters import NeonReadingSink
from silip.ingest.domain import InvalidReadingError
from silip.ingest.service import ingest
from silip.shared.config import get_settings
from silip.shared.db import connect

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _sink() -> NeonReadingSink:
    settings = get_settings()
    return NeonReadingSink(lambda: connect(settings))


def handle(event: dict[str, Any], context: object) -> dict[str, str]:
    """Store one reading. Invalid payloads are logged by field name and dropped."""
    try:
        reading = ingest(event, _sink())
    except InvalidReadingError as error:
        logger.warning("dropped reading: %s", error)
        return {"status": "rejected"}
    return {"status": "stored", "transformer_id": reading.transformer_id}
