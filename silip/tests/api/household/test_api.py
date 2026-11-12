import pandas as pd
import pytest

from silip.household.domain import HouseholdNotLinkedError
from silip.household.service import usage_for_account
from tests.api.helpers import auth


def test_usage_is_household_only(client):
    assert client.get("/api/v1/me/usage").status_code == 401
    assert client.get("/api/v1/me/usage", headers=auth("engineer-token")).status_code == 403


def test_usage_returns_own_week(client):
    body = client.get("/api/v1/me/usage", headers=auth("household-token")).json()
    assert body["is_simulated"]
    assert len(body["points"]) == 7 * 96
    assert body["total_kwh"] > 0


class UnlinkedSource:
    def sin_hash_for_account(self, subject: str) -> None:
        return None

    def household_usage(
        self, sin_hash: str
    ) -> pd.DataFrame:  # pragma: no cover - must not be called
        raise AssertionError("usage read without a linked household")


def test_unlinked_account_reads_nothing():
    with pytest.raises(HouseholdNotLinkedError):
        usage_for_account(UnlinkedSource(), "sub-x")  # type: ignore[arg-type]
