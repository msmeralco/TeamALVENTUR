"""Local ingest for rehearsals without the deployed API: same `ingest` service, piped readings.

    python -m silip.bench.sim --script --stdout | python -m silip.ingest.local

Deployed, devices (and the simulator with --http) post to /api/v1/devices/{clamp_id}/readings.
"""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Iterator
from typing import Any, TextIO

import psycopg

from silip.ingest.adapters import INSERT_SQL
from silip.ingest.domain import InvalidReadingError
from silip.ingest.service import ingest
from silip.shared.config import get_settings
from silip.shared.db import database_url
from silip_ml.readings.domain import Reading

logger = logging.getLogger(__name__)


class KeptOpenSink:
    """NeonReadingSink's insert on one long-lived connection: a new TLS connection per reading
    (about 0.5 s to Neon) cannot keep up with five homes every 2 s."""

    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection

    def write(self, reading: Reading) -> None:
        self._connection.execute(INSERT_SQL, reading.model_dump())


def messages(stream: TextIO) -> Iterator[dict[str, Any]]:
    for line in stream:
        if line.strip():
            yield json.loads(line)["payload"]


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    with psycopg.connect(database_url(get_settings()), autocommit=True) as connection:
        sink = KeptOpenSink(connection)
        for payload in messages(sys.stdin):
            try:
                ingest(payload, sink)
            except InvalidReadingError as error:
                logger.warning("dropped reading: %s", error)


if __name__ == "__main__":
    main()
