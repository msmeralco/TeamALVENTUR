"""Household-scoped electrical details, resolved exclusively through the token subject."""

from collections.abc import Callable

import psycopg
from psycopg.rows import dict_row

from silip.household.domain import ElectricalReading, HouseholdDevice


def device_for_account(
    subject: str, connect: Callable[[], psycopg.Connection]
) -> HouseholdDevice | None:
    with connect() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT c.clamp_id, h.transformer_id, h.lat, h.lon, h.location_label, c.ct_model, c.last_seen_at, (c.is_simulated OR h.is_simulated) AS is_simulated FROM household_account a JOIN household h USING (sin_hash) JOIN clamp c USING (sin_hash) WHERE a.cognito_sub = %s",
            (subject,),
        )
        device = cur.fetchone()
        if device is None:
            return None
        cur.execute(
            "SELECT r.ts, r.voltage_v, r.current_a, r.power_kw, r.power_factor, r.energy_kwh_interval, r.motion, r.event, r.is_simulated FROM reading r JOIN household_account a USING (sin_hash) WHERE a.cognito_sub = %s ORDER BY r.ts DESC LIMIT 192",
            (subject,),
        )
        return HouseholdDevice(
            **device, readings=[ElectricalReading.model_validate(row) for row in cur.fetchall()]
        )
