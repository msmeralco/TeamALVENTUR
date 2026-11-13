"""Neon device registry, transformer totals, and the single-device PoC usage query."""

from collections.abc import Callable
from hashlib import sha256
from secrets import token_urlsafe

import psycopg
from psycopg.rows import dict_row

from silip.devices.domain import (
    AggregatePoint,
    Device,
    DeviceKey,
    DeviceRegistration,
    DeviceSetup,
    DemoDeviceUsage,
    DemoUsagePoint,
    Installation,
    RegistryError,
    TransformerOption,
    TransformerRegistration,
    TransformerTelemetry,
)

DEVICE_SQL = """
SELECT c.clamp_id, h.transformer_id, h.lat, h.lon, h.location_label, c.ct_model, c.installed_at,
 c.last_seen_at, (c.device_key_hash IS NOT NULL) AS device_key_set, (c.is_simulated OR h.is_simulated) AS is_simulated,
 CASE WHEN c.last_seen_at >= now() - interval '60 minutes' THEN 'online'
      WHEN c.last_seen_at IS NULL THEN 'awaiting data' ELSE 'offline' END AS status
 FROM clamp c JOIN household h USING (sin_hash)
"""


class NeonDeviceRegistry:
    def __init__(self, connect: Callable[[], psycopg.Connection]) -> None:
        self._connect = connect

    def devices(self) -> list[Device]:
        with self._connect() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(DEVICE_SQL + " ORDER BY c.clamp_id")
            return [Device.model_validate(row) for row in cur.fetchall()]

    def demo_usage(self, clamp_id: str) -> DemoDeviceUsage | None:
        """Read seven days of aggregate usage for a registered PoC clamp, without its location."""
        with self._connect() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT c.clamp_id, h.transformer_id, c.last_seen_at,"
                " (c.is_simulated OR h.is_simulated) AS is_simulated, c.sin_hash"
                " FROM clamp c JOIN household h USING (sin_hash) WHERE c.clamp_id = %s",
                (clamp_id,),
            )
            device = cur.fetchone()
            if device is None:
                return None

            cur.execute(
                "SELECT date_bin('15 minutes', ts, TIMESTAMPTZ '2000-01-01') AS ts,"
                " avg(power_kw)::float8 AS kw, bool_or(is_simulated) AS is_simulated"
                " FROM reading WHERE sin_hash = %s"
                " AND ts > (SELECT max(ts) FROM reading WHERE sin_hash = %s) - interval '7 days'"
                " GROUP BY 1 ORDER BY 1",
                (device["sin_hash"], device["sin_hash"]),
            )
            rows = cur.fetchall()
            points = [DemoUsagePoint(ts=row["ts"], kw=row["kw"]) for row in rows]
            return DemoDeviceUsage(
                clamp_id=device["clamp_id"],
                transformer_id=device["transformer_id"],
                last_seen_at=device["last_seen_at"],
                total_kwh=round(sum(row["kw"] * 0.25 for row in rows), 2),
                is_simulated=bool(device["is_simulated"])
                or any(bool(row["is_simulated"]) for row in rows),
                points=points,
            )

    def transformers(self) -> list[TransformerOption]:
        with self._connect() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT transformer_id, lat, lon, is_simulated FROM transformer ORDER BY transformer_id"
            )
            return [TransformerOption.model_validate(row) for row in cur.fetchall()]

    def add_transformer(self, request: TransformerRegistration) -> TransformerOption:
        try:
            with self._connect() as conn, conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "INSERT INTO transformer (transformer_id, rated_kva, homes, coverage_pct, lat, lon, is_simulated) "
                    "VALUES (%(transformer_id)s, %(rated_kva)s, %(homes)s, %(coverage_pct)s, %(lat)s, %(lon)s, %(is_simulated)s) "
                    "RETURNING transformer_id, lat, lon, is_simulated",
                    request.model_dump(),
                )
                row = cur.fetchone()
                assert row is not None
                return TransformerOption.model_validate(row)
        except psycopg.errors.UniqueViolation:
            raise RegistryError("Transformer ID already exists") from None

    def register(self, request: DeviceRegistration) -> DeviceSetup:
        key = token_urlsafe(32)
        params = {**request.model_dump(), "device_key_hash": sha256(key.encode()).hexdigest()}
        try:
            with self._connect() as conn, conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT transformer_id, is_simulated FROM household WHERE sin_hash = %(sin_hash)s FOR UPDATE",
                    params,
                )
                household = cur.fetchone()
                if household and (
                    household["transformer_id"] != request.transformer_id
                    or household["is_simulated"] != request.is_simulated
                ):
                    raise RegistryError("Existing household assignment or simulation flag differs")
                cur.execute(
                    "INSERT INTO household (sin_hash, transformer_id, has_clamp, lat, lon, location_label, is_simulated) VALUES (%(sin_hash)s, %(transformer_id)s, true, %(lat)s, %(lon)s, %(location_label)s, %(is_simulated)s) ON CONFLICT (sin_hash) DO UPDATE SET has_clamp = true, lat = EXCLUDED.lat, lon = EXCLUDED.lon, location_label = EXCLUDED.location_label",
                    params,
                )
                cur.execute(
                    "INSERT INTO clamp (clamp_id, sin_hash, ct_model, installed_at, is_simulated, device_key_hash) VALUES (%(clamp_id)s, %(sin_hash)s, %(ct_model)s, now(), %(is_simulated)s, %(device_key_hash)s)",
                    params,
                )
                cur.execute(DEVICE_SQL + " WHERE c.clamp_id = %(clamp_id)s", params)
                row = cur.fetchone()
                assert row is not None
                return DeviceSetup.model_validate({**row, "device_key": key})
        except psycopg.errors.UniqueViolation:
            raise RegistryError("Device or household already registered") from None
        except psycopg.errors.ForeignKeyViolation:
            raise RegistryError("Transformer not found") from None

    def assign(self, clamp_id: str, request: Installation) -> Device:
        params = {**request.model_dump(), "clamp_id": clamp_id}
        try:
            with self._connect() as conn, conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "UPDATE household h SET transformer_id = %(transformer_id)s, lat = %(lat)s, lon = %(lon)s, location_label = %(location_label)s FROM clamp c WHERE c.sin_hash = h.sin_hash AND c.clamp_id = %(clamp_id)s RETURNING h.sin_hash",
                    params,
                )
                if cur.fetchone() is None:
                    raise RegistryError("Device not found")
                cur.execute(DEVICE_SQL + " WHERE c.clamp_id = %(clamp_id)s", params)
                return Device.model_validate(cur.fetchone())
        except psycopg.errors.ForeignKeyViolation:
            raise RegistryError("Transformer not found") from None

    def replace_key(self, clamp_id: str) -> DeviceKey:
        key = token_urlsafe(32)
        with self._connect() as conn:
            row = conn.execute(
                "UPDATE clamp SET device_key_hash = %s WHERE clamp_id = %s RETURNING clamp_id",
                (sha256(key.encode()).hexdigest(), clamp_id),
            ).fetchone()
            if row is None:
                raise RegistryError("Device not found")
        return DeviceKey(device_key=key)

    def aggregate(self, transformer_id: str) -> TransformerTelemetry:
        with self._connect() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT transformer_id FROM transformer WHERE transformer_id = %s",
                (transformer_id,),
            )
            if cur.fetchone() is None:
                raise RegistryError("Transformer not found")
            cur.execute(
                "SELECT count(*) AS count FROM clamp c JOIN household h USING (sin_hash) WHERE h.transformer_id = %s",
                (transformer_id,),
            )
            count_row = cur.fetchone()
            assert count_row is not None
            count = count_row["count"]
            # Average each home first so faster publishers do not inflate transformer load.
            cur.execute(
                """WITH per_home AS (
                SELECT sin_hash, date_bin('15 minutes', ts, TIMESTAMPTZ '2000-01-01') AS ts,
                avg(power_kw) AS kw, sum(energy_kwh_interval) AS kwh,
                bool_or(is_simulated) AS is_simulated FROM reading
                WHERE transformer_id = %s AND ts >= now() - interval '48 hours' AND ts <= now()
                GROUP BY 1, 2)
                SELECT ts, sum(kw)::float8 AS measured_kw, sum(kwh)::float8 AS energy_kwh,
                count(*) AS homes_reporting, bool_or(is_simulated) AS is_simulated
                FROM per_home GROUP BY ts ORDER BY ts""",
                (transformer_id,),
            )
            return TransformerTelemetry(
                transformer_id=transformer_id,
                registered_homes=count,
                points=[AggregatePoint.model_validate(row) for row in cur.fetchall()],
            )
