"""`GET /api/v1/me/usage` for signed-in households."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from silip.household import service
from silip.household.domain import HouseholdNotLinkedError, HouseholdUsage
from silip.shared.auth.api import AUTH_RESPONSES, Household
from silip.shared.deps import Source

router = APIRouter(prefix="/api/v1/me", tags=["household"])


@router.get("/usage", response_model=HouseholdUsage, responses=AUTH_RESPONSES)
def my_usage(source: Source, user: Household) -> HouseholdUsage:
    """The signed-in household's own last 7 days of usage."""
    try:
        return service.usage_for_account(source, user.subject)
    except HouseholdNotLinkedError as error:
        raise HTTPException(
            status_code=404, detail="No household is linked to this account"
        ) from error
