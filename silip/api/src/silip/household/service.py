"""Resolve the account's household server-side, then read its usage."""

from __future__ import annotations

from silip.household.domain import (
    HOURS_PER_INTERVAL,
    HouseholdNotLinkedError,
    HouseholdUsage,
    UsagePoint,
)
from silip.shared.readings.domain import DataSource


def usage_for_account(source: DataSource, subject: str) -> HouseholdUsage:
    """Usage for the household linked to `subject` (the token's `sub`).

    The sin_hash never comes from the request, so one household cannot read another's data.

    Raises:
        HouseholdNotLinkedError: if no household is linked to the account.
    """
    sin_hash = source.sin_hash_for_account(subject)
    if sin_hash is None:
        raise HouseholdNotLinkedError(subject)
    usage = source.household_usage(sin_hash)
    return HouseholdUsage(
        total_kwh=round(float(usage["power_kw"].sum() * HOURS_PER_INTERVAL), 2),
        points=[
            UsagePoint(ts=ts, kw=kw) for ts, kw in zip(usage["ts"], usage["power_kw"], strict=True)
        ],
        is_simulated=bool(usage["is_simulated"].all()) if len(usage) else True,
    )
