"""Legacy Lambda entry point for an IoT Core topic rule. Not wired in infra: devices post HTTPS to the API.

The rule must pass the MQTT client and topic:
`SELECT *, clientid() AS client_id, topic() AS topic FROM 'silip/v1/+/+/reading'`.
"""

from __future__ import annotations

import logging
from typing import Any

from silip.ingest.adapters import NeonReadingSink
from silip.ingest.domain import InvalidReadingError
from silip.ingest.service import ingest
from silip.shared.config import get_settings
from silip.shared.db import connect

logger = logging.getLogger(__name__)


def _sink(client_id: str, topic: str) -> NeonReadingSink:
    settings = get_settings()
    return NeonReadingSink(lambda: connect(settings), client_id, topic)


def handle(event: dict[str, Any], context: object) -> dict[str, str]:
    """Store one reading. Invalid payloads are logged by field name and dropped."""
    client_id, topic = event.pop("client_id", None), event.pop("topic", None)
    if not isinstance(client_id, str) or not isinstance(topic, str):
        logger.warning("dropped reading: the IoT rule must pass client_id and topic")
        return {"status": "rejected"}
    try:
        reading = ingest(event, _sink(client_id, topic))
    except InvalidReadingError as error:
        logger.warning("dropped reading: %s", error)
        return {"status": "rejected"}
    return {"status": "stored", "transformer_id": reading.transformer_id}
