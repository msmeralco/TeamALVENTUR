"""Outage routes: the list is public (area only); the detail is engineer-only."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from silip.outages import service
from silip.outages.domain import OutageDetail, OutageNotFoundError, OutageSummary, Status
from silip.shared.auth.api import AUTH_RESPONSES, Engineer
from silip.shared.config import Settings
from silip.shared.deps import Source

router = APIRouter(prefix="/api/v1/outages", tags=["outages"])


@router.get("", response_model=list[OutageSummary])
def list_outages(
    source: Source, settings: Settings, status: Status | None = "open"
) -> list[OutageSummary]:
    """Public: outages by area with a restoration range. No household or exact pin data."""
    return service.list_outages(source, settings.outage_locator, settings.eta_estimator, status)


@router.get("/{outage_id}", response_model=OutageDetail, responses=AUTH_RESPONSES)
def get_outage(outage_id: str, source: Source, settings: Settings, _: Engineer) -> OutageDetail:
    """Engineer: exact pin, transformer, last-gasp and report counts."""
    try:
        return service.outage_detail(
            source, settings.outage_locator, settings.eta_estimator, outage_id
        )
    except OutageNotFoundError as error:
        raise HTTPException(status_code=404, detail="Outage not found") from error
