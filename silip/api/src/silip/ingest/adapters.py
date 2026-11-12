"""Neon implementation of the reading sink."""

from __future__ import annotations

from collections.abc import Callable

import psycopg

from silip_ml.readings.domain import Reading

INSERT_SQL = (
    "INSERT INTO reading (sin_hash, transformer_id, ts, voltage_v, current_a, power_kw,"
    " power_factor, energy_kwh_interval, event, is_simulated)"
    " VALUES (%(sin_hash)s, %(transformer_id)s, %(ts)s, %(voltage_v)s, %(current_a)s, %(power_kw)s,"
    " %(power_factor)s, %(energy_kwh_interval)s, %(event)s, %(is_simulated)s)"
    " ON CONFLICT (sin_hash, ts) DO NOTHING"
)


class NeonReadingSink:
    """Idempotent insert: the device may resend after a reconnect."""

    def __init__(self, connect: Callable[[], psycopg.Connection]) -> None:
        self._connect = connect

    def write(self, reading: Reading) -> None:
        with self._connect() as connection:
            connection.execute(INSERT_SQL, reading.model_dump())
