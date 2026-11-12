"""Locate outages and estimate restoration with the configured strategies."""

from __future__ import annotations

from collections.abc import Hashable, Mapping
from typing import Any

import pandas as pd

from silip.outages.domain import (
    PUBLIC_COORDINATE_DECIMALS,
    OutageDetail,
    OutageNotFoundError,
    OutageSummary,
    Status,
)
from silip.shared.readings.domain import DataSource
from silip_ml.core.registry import create


def _assessed(source: DataSource, locator: str, estimator: str) -> pd.DataFrame:
    outages, signals = source.outages(), source.outage_signals()
    as_of = source.load()["ts"].max()
    ends = outages["start_ts"] + pd.to_timedelta(outages["duration_min"], unit="min")
    restored = ends.notna() & (ends <= as_of)
    pins = (
        create("outage_locator", locator)
        .locate(signals)
        .rename(columns={"lat": "pin_lat", "lon": "pin_lon"})
    )
    eta = create("eta_estimator", estimator).fit(outages[restored]).predict(outages)
    counts = signals.pivot_table(
        index="outage_id", columns="kind", values="ts", aggfunc="count", fill_value=0
    )
    return (
        outages.assign(status=restored.map({True: "restored", False: "open"}))
        .merge(pins, on="outage_id", how="left")
        .merge(eta, on="outage_id")
        .merge(counts.reset_index(), on="outage_id", how="left")
        .fillna({"last_gasp": 0, "report": 0})
    )


def _summary_fields(row: Mapping[Hashable, Any]) -> dict[str, Any]:
    return {
        "outage_id": row["outage_id"],
        "status": row["status"],
        "cause": row["cause"],
        "started_at": row["start_ts"],
        "area_lat": round(row["pin_lat"], PUBLIC_COORDINATE_DECIMALS),
        "area_lon": round(row["pin_lon"], PUBLIC_COORDINATE_DECIMALS),
        "eta_p10_min": row["eta_p10_min"],
        "eta_p50_min": row["eta_p50_min"],
        "eta_p90_min": row["eta_p90_min"],
        "is_simulated": bool(row["is_simulated"]),
    }


def list_outages(
    source: DataSource, locator: str, estimator: str, status: Status | None
) -> list[OutageSummary]:
    """Outages, newest first; filtered by status when given."""
    assessed = _assessed(source, locator, estimator).sort_values("start_ts", ascending=False)
    if status is not None:
        assessed = assessed[assessed["status"] == status]
    return [OutageSummary(**_summary_fields(row)) for row in assessed.to_dict("records")]


def outage_detail(source: DataSource, locator: str, estimator: str, outage_id: str) -> OutageDetail:
    """One outage with its exact pin and signal counts."""
    assessed = _assessed(source, locator, estimator)
    match = assessed[assessed["outage_id"] == outage_id]
    if match.empty:
        raise OutageNotFoundError(outage_id)
    row = match.to_dict("records")[0]
    return OutageDetail(
        **_summary_fields(row),
        transformer_id=row["transformer_id"],
        pin_lat=row["pin_lat"],
        pin_lon=row["pin_lon"],
        last_gasp_count=int(row["last_gasp"]),
        report_count=int(row["report"]),
    )
