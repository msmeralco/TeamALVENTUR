"""Neon implementation of the reading sink."""

from __future__ import annotations

from collections.abc import Callable
from hashlib import sha256
from hmac import compare_digest

import psycopg
from psycopg.types.json import Jsonb

from silip.ingest.domain import DeviceAuthenticationError, InvalidReadingError
from silip.ingest.service import ingest
from silip_ml.readings.domain import DeviceReading, Reading

INSERT_SQL = (
    "INSERT INTO reading (sin_hash, transformer_id, ts, voltage_v, current_a, power_kw,"
    " power_factor, energy_kwh_interval, event, is_simulated, motion)"
    " VALUES (%(sin_hash)s, %(transformer_id)s, %(ts)s, %(voltage_v)s, %(current_a)s, %(power_kw)s,"
    " %(power_factor)s, %(energy_kwh_interval)s, %(event)s, %(is_simulated)s, %(motion)s)"
    " ON CONFLICT (sin_hash, ts) DO NOTHING"
)


class NeonReadingSink:
    """Idempotent insert: the device may resend after a reconnect."""

    def __init__(
        self, connect: Callable[[], psycopg.Connection], client_id: str, topic: str
    ) -> None:
        self._connect = connect
        self._client_id = client_id
        self._topic = topic

    def write(self, reading: Reading) -> None:
        with self._connect() as connection:
            if self._topic != f"silip/v1/{reading.transformer_id}/{reading.sin_hash}/reading":
                raise InvalidReadingError("topic does not match payload")
            # Lock the household assignment against concurrent installation changes.
            row = connection.execute(
                "SELECT h.sin_hash, h.transformer_id, (c.is_simulated OR h.is_simulated)"
                " FROM clamp c JOIN household h USING (sin_hash) WHERE c.clamp_id = %s"
                " FOR UPDATE OF h, c",
                (self._client_id,),
            ).fetchone()
            if row is None or tuple(row) != (
                reading.sin_hash,
                reading.transformer_id,
                reading.is_simulated,
            ):
                raise InvalidReadingError("device is unregistered or assignment does not match")
            params = reading.model_dump()
            params["motion"] = Jsonb(params["motion"]) if params["motion"] is not None else None
            connection.execute(INSERT_SQL, params)
            connection.execute(
                "UPDATE clamp SET last_seen_at = GREATEST(last_seen_at, %s) WHERE clamp_id = %s",
                (reading.ts, self._client_id),
            )


class _TransactionSink:
    def __init__(self, connection: psycopg.Connection, client_id: str) -> None:
        self.connection = connection
        self.client_id = client_id

    def write(self, reading: Reading) -> None:
        params = reading.model_dump()
        params["motion"] = Jsonb(params["motion"]) if params["motion"] is not None else None
        self.connection.execute(INSERT_SQL, params)
        self.connection.execute(
            "UPDATE clamp SET last_seen_at = GREATEST(last_seen_at, %s) WHERE clamp_id = %s",
            (reading.ts, self.client_id),
        )


class HttpReadingReceiver:
    def __init__(self, connect: Callable[[], psycopg.Connection]) -> None:
        self._connect = connect

    def receive(self, clamp_id: str, key: str, payload: DeviceReading) -> None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT h.sin_hash, h.transformer_id, (c.is_simulated OR h.is_simulated), c.device_key_hash"
                " FROM clamp c JOIN household h USING (sin_hash) WHERE c.clamp_id = %s"
                " FOR UPDATE OF h, c",
                (clamp_id,),
            ).fetchone()
            expected = row[3] if row and row[3] else "0" * 64
            valid = compare_digest(sha256(key.encode()).hexdigest(), expected)
            if not row or not row[3] or not valid:
                raise DeviceAuthenticationError("Invalid device key")
            body = payload.model_dump(exclude={"sin_hash", "transformer_id"})
            body.update(
                sin_hash=row[0],
                transformer_id=row[1],
                is_simulated=bool(row[2]) or payload.is_simulated,
            )
            ingest(body, _TransactionSink(conn, clamp_id))
