from unittest.mock import MagicMock

import pytest

from silip.app import app
from silip.devices.api import registry
from silip.devices.domain import (
    DeviceRegistration,
    RegistryError,
    TransformerOption,
    TransformerRegistration,
)
from silip.devices.service import register
from tests.api.helpers import auth

REQUEST = {
    "clamp_id": "node-1",
    "sin_hash": "a" * 64,
    "transformer_id": "T-104",
    "lat": 14.5,
    "lon": 121.0,
    "location_label": "24 Sampaguita St., near the barangay hall",
    "consent_confirmed": True,
}


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/devices",
        "/api/v1/devices/transformers",
        "/api/v1/devices/transformers/T-104/telemetry",
    ],
)
def test_device_views_are_engineer_only(client, path):
    assert client.get(path).status_code == 401
    assert client.get(path, headers=auth("household-token")).status_code == 403


def test_registration_requires_consent_and_real_hash():
    store = MagicMock()
    for changes in ({"consent_confirmed": False}, {"sin_hash": "0" * 64}):
        with pytest.raises(RegistryError):
            register(DeviceRegistration(**{**REQUEST, **changes}), store)
    store.register.assert_not_called()


def test_registration_forbidden_to_household_and_conflict_reported(client):
    store = MagicMock()
    store.register.side_effect = RegistryError("Device or household already registered")
    app.dependency_overrides[registry] = lambda: store
    try:
        assert (
            client.post(
                "/api/v1/devices", json=REQUEST, headers=auth("household-token")
            ).status_code
            == 403
        )
        store.register.assert_not_called()
        result = client.post("/api/v1/devices", json=REQUEST, headers=auth("engineer-token"))
        assert result.status_code == 409
        assert "already registered" in result.json()["detail"]
    finally:
        app.dependency_overrides.pop(registry)


def test_transformer_can_be_added_by_engineer_only(client):
    store = MagicMock()
    store.add_transformer.return_value = TransformerOption(
        transformer_id="T-150", lat=14.5, lon=121.0, is_simulated=True
    )
    app.dependency_overrides[registry] = lambda: store
    body = {
        "transformer_id": "T-150",
        "rated_kva": 50,
        "lat": 14.5,
        "lon": 121.0,
        "homes": 20,
        "coverage_pct": 0.2,
        "is_simulated": True,
    }
    try:
        denied = client.post(
            "/api/v1/devices/transformers", json=body, headers=auth("household-token")
        )
        assert denied.status_code == 403
        store.add_transformer.assert_not_called()

        created = client.post(
            "/api/v1/devices/transformers", json=body, headers=auth("engineer-token")
        )
        assert created.status_code == 201
        assert created.json() == {
            "transformer_id": "T-150",
            "lat": 14.5,
            "lon": 121.0,
            "is_simulated": True,
        }
        store.add_transformer.assert_called_once_with(TransformerRegistration(**body))
    finally:
        app.dependency_overrides.pop(registry)
