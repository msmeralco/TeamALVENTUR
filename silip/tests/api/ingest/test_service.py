import pytest

from silip.ingest.domain import InvalidReadingError
from silip.ingest.service import ingest
from silip_ml.core.privacy import sin_hash
from silip_ml.readings.domain import Reading

PAYLOAD = {
    "sin_hash": sin_hash("example", "salt"),
    "transformer_id": "T-104",
    "ts": "2026-11-12T21:15:00+08:00",
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
