from datetime import UTC, datetime
from hashlib import sha256
from unittest.mock import MagicMock

import pytest

from silip.ingest.adapters import HttpReadingReceiver
from silip.ingest.domain import DeviceAuthenticationError
from silip_ml.readings.domain import DeviceReading


def payload():
    return DeviceReading(
        ts=datetime.now(UTC),
        voltage_v=220,
        current_a=2,
        power_kw=0.4,
        power_factor=0.9,
        energy_kwh_interval=0.1,
        sin_hash="b" * 64,
        transformer_id="untrusted-assignment",
    )


def test_device_key_required_even_with_local_auth_disabled(client):
    result = client.post("/api/v1/devices/node-1/readings", json=payload().model_dump(mode="json"))
    assert result.status_code == 401


@pytest.mark.parametrize(
    "row",
    [
        None,
        ("a" * 64, "T-1", False, None),
        ("a" * 64, "T-1", False, sha256(b"correct-key").hexdigest()),
    ],
)
def test_invalid_key_cannot_insert_readings(row):
    conn = MagicMock()
    conn.__enter__.return_value = conn
    conn.execute.return_value.fetchone.return_value = row
    with pytest.raises(DeviceAuthenticationError):
        HttpReadingReceiver(lambda: conn).receive("node-1", "wrong-key", payload())
    assert conn.execute.call_count == 1


def test_http_assignments_come_from_registry_not_payload():
    conn = MagicMock()
    conn.__enter__.return_value = conn
    conn.execute.return_value.fetchone.return_value = (
        "a" * 64,
        "assigned-transformer",
        True,
        sha256(b"device-key").hexdigest(),
    )
    HttpReadingReceiver(lambda: conn).receive("node-1", "device-key", payload())
    inserted = conn.execute.call_args_list[1].args[1]
    assert inserted["sin_hash"] == "a" * 64
    assert inserted["transformer_id"] == "assigned-transformer"
    assert inserted["is_simulated"] is True
    assert conn.execute.call_count == 3
