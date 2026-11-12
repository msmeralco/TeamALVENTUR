"""Neon reads for the bench rig. The SQL itself names the bench transformers, so nothing else can leak."""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import datetime

import pandas as pd
import psycopg

from silip.shared.bench import config

# `= ANY(ids)` uses the (transformer_id, ts) index; `LIKE 'BENCH-%'` would scan every reading.
RECENT_SQL = (
    "SELECT sin_hash, transformer_id, ts, voltage_v, power_kw, event, is_simulated FROM reading"
    " WHERE transformer_id = ANY(%(ids)s) AND ts > %(since)s ORDER BY ts"
)
COLUMNS = ["sin_hash", "transformer_id", "ts", "voltage_v", "power_kw", "event", "is_simulated"]
BENCH_IDS = [t.transformer_id for t in config.TRANSFORMERS]


class NeonBenchReadings:
    """Keeps one connection open: the /demo page polls every 2 s, and a new TLS connection to Neon
    costs about a second each time."""

    def __init__(self, connect: Callable[[], psycopg.Connection]) -> None:
        self._connect = connect
        self._connection: psycopg.Connection | None = None
        self._lock = threading.Lock()

    def _query(self, since: datetime) -> list[tuple]:
        if self._connection is None or self._connection.closed:
            self._connection = self._connect()
            self._connection.autocommit = True
        with self._connection.cursor() as cursor:
            cursor.execute(RECENT_SQL, {"ids": BENCH_IDS, "since": since})
            return cursor.fetchall()

    def recent(self, since: datetime) -> pd.DataFrame:
        with self._lock:
            try:
                rows = self._query(since)
            except psycopg.OperationalError:
                self._connection = None  # dropped by Neon while idle: reconnect once
                rows = self._query(since)
        frame = pd.DataFrame(rows, columns=COLUMNS)
        # sin_hash is char(64); strip any padding so it matches the config's hashes.
        frame["sin_hash"] = frame["sin_hash"].str.strip()
        return frame
