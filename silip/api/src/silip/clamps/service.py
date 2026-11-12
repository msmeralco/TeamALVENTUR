"""Clamp status on the data's own clock."""

from __future__ import annotations

from collections.abc import Hashable, Mapping
from typing import Any

import pandas as pd

from silip.clamps.domain import ClampMap, ClampPoint, ClampStatus
from silip.shared.geo import BoundingBox
from silip.shared.readings.domain import DataSource

# Four missed 15-minute readings. Design choice, no source: [VERIFY] against field reconnect data.
OFFLINE_AFTER = pd.Timedelta(minutes=60)


def status(last_seen_at: pd.Timestamp | None, as_of: pd.Timestamp) -> ClampStatus:
    """Offline when never seen or silent for longer than OFFLINE_AFTER before `as_of`."""
    if last_seen_at is None or pd.isna(last_seen_at) or as_of - last_seen_at > OFFLINE_AFTER:
        return "offline"
    return "online"


def _point(row: Mapping[Hashable, Any], as_of: pd.Timestamp) -> ClampPoint:
    last_seen = None if pd.isna(row["last_seen_at"]) else row["last_seen_at"]
    return ClampPoint(
        clamp_id=row["clamp_id"],
        transformer_id=row["transformer_id"],
        lat=row["lat"],
        lon=row["lon"],
        ct_model=row["ct_model"],
        installed_at=row["installed_at"],
        last_seen_at=last_seen,
        status=status(last_seen, as_of),
        is_simulated=bool(row["is_simulated"]),
    )


def clamp_map(source: DataSource, bbox: BoundingBox | None) -> ClampMap:
    """Every clamp inside `bbox` (all when None), sorted by transformer then clamp."""
    offline_after_min = int(OFFLINE_AFTER.total_seconds() // 60)
    clamps = source.clamps()
    as_of = clamps["last_seen_at"].max() if not clamps.empty else None
    if as_of is None or pd.isna(as_of):
        return ClampMap(
            as_of=None, offline_after_min=offline_after_min, clamps=[], is_simulated=False
        )
    points = sorted(
        (
            _point(row, as_of)
            for row in clamps.to_dict("records")
            if bbox is None or bbox.contains(row["lat"], row["lon"])
        ),
        key=lambda p: (p.transformer_id, p.clamp_id),
    )
    return ClampMap(
        as_of=as_of,
        offline_after_min=offline_after_min,
        clamps=points,
        is_simulated=bool(clamps["is_simulated"].any()),
    )
