"""Engineer-only route: clamp devices for the risk map."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from silip.clamps import service
from silip.clamps.domain import ClampMap
from silip.shared.auth.api import AUTH_RESPONSES, Engineer
from silip.shared.deps import Source
from silip.shared.geo import BoundingBox

router = APIRouter(prefix="/api/v1/clamps", tags=["clamps"])


@router.get("", response_model=ClampMap, responses=AUTH_RESPONSES)
def list_clamps(
    source: Source,
    _: Engineer,
    bbox: Annotated[str | None, Query(description="min_lon,min_lat,max_lon,max_lat")] = None,
) -> ClampMap:
    """Each clamp's device details and online/offline status. No household identity or usage."""
    try:
        box = BoundingBox.parse(bbox) if bbox else None
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return service.clamp_map(source, box)
