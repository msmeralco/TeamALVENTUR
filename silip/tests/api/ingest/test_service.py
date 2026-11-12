import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from silip.ingest.adapters import NeonReadingSink
from silip.ingest.domain import InvalidReadingError
from silip.ingest.service import ingest
from silip_ml.core.privacy import sin_hash
from silip_ml.readings.domain import Reading

PAYLOAD = {
    "sin_hash": sin_hash("example", "salt"),
    "transformer_id": "T-104",
    "ts": datetime.now(UTC).isoformat(),
    "voltage_v": 219.8,
    "current_a": 11.6,
    "power_kw": 2.43,
    "power_factor": 0.95,
    "energy_kwh_interval": 0.61,
    "event": None,
}


class ListSink:
    def __init__(self) -> None:
        self.written: list[Reading] = []

    def write(self, reading: Reading) -> None:
        self.written.append(reading)


def test_valid_payload_is_written():
    sink = ListSink()
    ingest(PAYLOAD, sink)
    assert [r.transformer_id for r in sink.written] == ["T-104"]


def test_invalid_payload_names_fields_not_values():
    sink = ListSink()
    with pytest.raises(InvalidReadingError) as error:
        ingest({**PAYLOAD, "sin_hash": "not-a-hash"}, sink)
    assert "sin_hash" in str(error.value) and "not-a-hash" not in str(error.value)
    assert sink.written == []


def test_future_clock_is_rejected_before_writing():
    sink = ListSink()
    with pytest.raises(InvalidReadingError, match="clock tolerance"):
        ingest({**PAYLOAD, "ts": (datetime.now(UTC) + timedelta(hours=1)).isoformat()}, sink)
    assert not sink.written


def test_example_motion_contract_can_be_received():
    payload = json.loads(Path("iot/payload.example.json").read_text())
    payload["ts"] = datetime.now(UTC).isoformat()
    reading = ingest(payload, ListSink())
    assert reading.motion and reading.motion.state == "wiggling"


@pytest.mark.parametrize(
    "registered", [None, (PAYLOAD["sin_hash"], "different-transformer", False)]
)
def test_unregistered_or_wrong_assignment_does_not_insert(registered):
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.execute.return_value.fetchone.return_value = registered
    sink = NeonReadingSink(
        lambda: connection, "node-1", f"silip/v1/T-104/{PAYLOAD['sin_hash']}/reading"
    )
    with pytest.raises(InvalidReadingError, match="assignment"):
        ingest(PAYLOAD, sink)
    assert connection.execute.call_count == 1


def test_mismatched_topic_does_not_touch_database():
    connection = MagicMock()
    connection.__enter__.return_value = connection
    sink = NeonReadingSink(lambda: connection, "node-1", "wrong-topic")
    with pytest.raises(InvalidReadingError, match="topic"):
        ingest(PAYLOAD, sink)
    connection.execute.assert_not_called()


def test_registered_reading_inserts_and_advances_last_seen_atomically():
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.execute.return_value.fetchone.return_value = (PAYLOAD["sin_hash"], "T-104", False)
    sink = NeonReadingSink(
        lambda: connection, "node-1", f"silip/v1/T-104/{PAYLOAD['sin_hash']}/reading"
    )
    ingest(PAYLOAD, sink)
    assert connection.execute.call_count == 3
    assert "ON CONFLICT" in connection.execute.call_args_list[1].args[0]
    assert "GREATEST" in connection.execute.call_args_list[2].args[0]
