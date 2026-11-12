"""The clamp reading payload and the load formula. Single source of truth for both.

`python -m silip_ml.readings.domain schemas/reading.json` exports the payload as JSON Schema
for the firmware (iot/) and anyone else outside Python.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

SIN_HASH_PATTERN = r"^[0-9a-f]{64}$"
READING_TOPIC = "silip/v1/{transformer_id}/{sin_hash}/reading"

# kVA rating -> usable kW, per the silip-domain skill: load_pct = kW / (rated_kva * 0.9).
ASSUMED_POWER_FACTOR = 0.9
INTERVAL = "15min"
STEPS_PER_HOUR = 4
STEPS_PER_DAY = 96
STEPS_PER_WEEK = 7 * STEPS_PER_DAY


class MotionAxes(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    x: float
    y: float
    z: float


class Motion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sensor: Literal["MPU6050"]
    accel_m_s2: MotionAxes
    gyro_dps: MotionAxes
    state: Literal["stable", "wiggling"]
    tamper_assessment: Literal["normal", "suspected_tampering"]


class Measurements(BaseModel):
    """One clamp node message (topic `READING_TOPIC`). Matches docs/SPEC.md#hardware."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    ts: AwareDatetime
    voltage_v: float = Field(ge=0, le=300)
    current_a: float = Field(ge=0, le=100, description="SCT-013-000 range is 0 to 100 A")
    power_kw: float = Field(description="Negative when rooftop solar exports")
    power_factor: float = Field(ge=0, le=1)
    energy_kwh_interval: float
    motion: Motion | None = None
    event: Literal["last_gasp"] | None = None
    is_simulated: bool = False


class Reading(Measurements):
    """Stored reading with a server-assigned household and transformer."""

    sin_hash: str = Field(pattern=SIN_HASH_PATTERN, description="Salted household reference")
    transformer_id: str = Field(min_length=1, max_length=32)


class DeviceReading(Measurements):
    """HTTP device report. Legacy identifiers are accepted but assignment is server-owned."""

    sin_hash: str | None = Field(default=None, pattern=SIN_HASH_PATTERN)
    transformer_id: str | None = Field(default=None, min_length=1, max_length=32)


def load_pct(transformer_kw: np.ndarray | float, rated_kva: np.ndarray | float) -> np.ndarray:
    """Share of the transformer's usable rating in use (1.0 = 100%)."""
    return np.asarray(transformer_kw) / (np.asarray(rated_kva) * ASSUMED_POWER_FACTOR)


def export_json_schema(path: Path, *, device: bool = False) -> None:
    """Write the Reading JSON Schema to `path`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps((DeviceReading if device else Reading).model_json_schema(), indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    export_json_schema(
        Path(sys.argv[1] if len(sys.argv) > 1 else "schemas/reading.json"),
        device=len(sys.argv) > 2 and sys.argv[2] == "device",
    )
