"""Clamp status on the data's own clock."""

from __future__ import annotations

from collections.abc import Hashable, Mapping
from typing import Any

import pandas as pd

from silip.clamps.domain import (
    ClampMap,
    ClampPoint,
    ClampStatus,
    ClampTotals,
    CoverageMap,
    TransformerCoverage,
)
from silip.dashboard.domain import (
    MIN_TRUST_REPORTING,
    TARGET_COVERAGE,
    by_transformer,
    clamp_health,
    clamps_to_target,
)
from silip.shared.geo import BoundingBox, within
from silip.shared.readings.domain import OFFLINE_AFTER, DataSource


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
    as_of = None if clamps.empty else pd.Timestamp.now(tz="UTC")
    if not clamps.empty and clamps["is_simulated"].all():
        latest = clamps["last_seen_at"].max()
        if pd.notna(latest):
            as_of = latest
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


def coverage(source: DataSource, bbox: BoundingBox | None) -> CoverageMap:
    """Clamp health per transformer inside `bbox`, judged at the latest load interval (the
    data's own clock, as scoring does). Counted where the data lives."""
    offline_after_min = int(OFFLINE_AFTER.total_seconds() // 60)
    as_of = source.latest_load_ts()
    transformers = within(source.transformers(), bbox)
    counts = by_transformer(source.clamp_counts(as_of.to_pydatetime())) if as_of else {}
    rows = []
    for row in transformers.to_dict("records"):
        tid = str(row["transformer_id"])
        found = counts.get(tid, {})
        health = clamp_health(
            int(row["homes"]),
            int(found.get("clamps_installed", 0)),
            int(found.get("clamps_online", 0)),
        )
        rows.append(
            TransformerCoverage(
                transformer_id=tid,
                lat=row["lat"],
                lon=row["lon"],
                clamp_health=health,
                clamps_to_target=clamps_to_target(health.homes, health.clamps_online),
                is_simulated=bool(row["is_simulated"]) or bool(found.get("is_simulated")),
            )
        )
    rows.sort(key=lambda r: (r.clamp_health.reporting_pct, r.transformer_id))
    return CoverageMap(
        as_of=None if as_of is None else as_of.to_pydatetime(),
        offline_after_min=offline_after_min,
        target_coverage=TARGET_COVERAGE,
        min_trust_reporting=MIN_TRUST_REPORTING,
        clamps=ClampTotals(
            installed=sum(r.clamp_health.clamps_installed for r in rows),
            online=sum(r.clamp_health.clamps_online for r in rows),
        ),
        transformers=rows,
        is_simulated=any(r.is_simulated for r in rows),
    )
