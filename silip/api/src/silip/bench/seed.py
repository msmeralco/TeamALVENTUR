"""Seed the bench rig's transformers and mock households. Safe to run again (inserts only).

    python -m silip.bench.seed

The rig is physical, so its transformer and household rows are is_simulated=false. Readings carry
their own flag: false from the rig, true from the simulator or a replay.
"""

from __future__ import annotations

from silip.shared.bench import config
from silip.shared.config import get_settings
from silip.shared.db import connect

TRANSFORMER_SQL = (
    "INSERT INTO transformer (transformer_id, rated_kva, homes, coverage_pct, lat, lon, is_simulated)"
    " VALUES (%(id)s, %(rated_kva)s, %(homes)s, 1, %(lat)s, %(lon)s, false)"
    " ON CONFLICT (transformer_id) DO NOTHING"
)
HOUSEHOLD_SQL = (
    "INSERT INTO household (sin_hash, transformer_id, has_clamp, is_simulated, lat, lon)"
    " VALUES (%(sin_hash)s, %(transformer_id)s, true, false, %(lat)s, %(lon)s)"
    " ON CONFLICT (sin_hash) DO NOTHING"
)


def seed() -> None:
    sites = {t.transformer_id: t for t in config.TRANSFORMERS}
    with connect(get_settings()) as connection:
        for t in config.TRANSFORMERS:
            homes = sum(h.record_transformer == t.transformer_id for h in config.HOMES)
            connection.execute(
                TRANSFORMER_SQL,
                {
                    "id": t.transformer_id,
                    "rated_kva": t.rated_kva,
                    "homes": homes,
                    "lat": t.lat,
                    "lon": t.lon,
                },
            )
        for home in config.HOMES:
            # The record (not the wiring) is what the utility's database holds.
            site = sites[home.record_transformer]
            connection.execute(
                HOUSEHOLD_SQL,
                {
                    "sin_hash": home.sin_hash,
                    "transformer_id": home.record_transformer,
                    "lat": site.lat,
                    "lon": site.lon,
                },
            )
    print(f"seeded {len(config.TRANSFORMERS)} bench transformers and {len(config.HOMES)} homes")


if __name__ == "__main__":
    seed()
