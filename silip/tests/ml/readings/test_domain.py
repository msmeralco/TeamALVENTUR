import json

import pandas as pd
import pytest
from pydantic import ValidationError

from silip_ml.core.privacy import sin_hash
from silip_ml.readings.aggregate import sum_by_transformer
from silip_ml.readings.domain import Reading, export_json_schema

VALID = {
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


def test_reading_accepts_spec_payload():
    assert Reading.model_validate(VALID).transformer_id == "T-104"


@pytest.mark.parametrize(
    "field,value", [("sin_hash", "12345678901"), ("ts", "2026-11-12T21:15:00")]
)
def test_reading_rejects_raw_sin_and_naive_time(field, value):
    with pytest.raises(ValidationError):
        Reading.model_validate({**VALID, field: value})


def test_exported_schema_matches_model(tmp_path):
    path = tmp_path / "reading.json"
    export_json_schema(path)
    assert json.loads(path.read_text()) == Reading.model_json_schema()


def test_sum_by_transformer_resamples_then_sums_homes():
    ts = pd.to_datetime(["2026-04-01 00:00", "2026-04-01 00:05", "2026-04-01 00:00"]).tz_localize(
        "Asia/Manila"
    )
    readings = pd.DataFrame(
        {
            "sin_hash": ["a", "a", "b"],
            "transformer_id": "T-1",
            "ts": ts,
            "power_kw": [1.0, 3.0, 0.5],
        }
    )
    result = sum_by_transformer(readings)
    assert result["measured_kw"].tolist() == [2.5]  # mean(1, 3) + 0.5
    assert result["homes_reporting"].tolist() == [2]
