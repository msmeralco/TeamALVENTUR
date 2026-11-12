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


class Reading(BaseModel):
    """One clamp node message (topic `READING_TOPIC`). Matches docs/SPEC.md#hardware."""

    model_config = ConfigDict(extra="forbid")

    sin_hash: str = Field(pattern=SIN_HASH_PATTERN, description="Salted SHA-256 of the SIN")
    transformer_id: str = Field(min_length=1, max_length=32)
    ts: AwareDatetime
    voltage_v: float = Field(ge=0, le=300)
    current_a: float = Field(ge=0, le=100, description="SCT-013-000 range is 0 to 100 A")
    power_kw: float = Field(description="Negative when rooftop solar exports")
    power_factor: float = Field(ge=0, le=1)
    energy_kwh_interval: float
    event: Literal["last_gasp"] | None = None
    is_simulated: bool = False


def load_pct(transformer_kw: np.ndarray | float, rated_kva: np.ndarray | float) -> np.ndarray:
    """Share of the transformer's usable rating in use (1.0 = 100%)."""
    return np.asarray(transformer_kw) / (np.asarray(rated_kva) * ASSUMED_POWER_FACTOR)


def export_json_schema(path: Path) -> None:
    """Write the Reading JSON Schema to `path`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(Reading.model_json_schema(), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    export_json_schema(Path(sys.argv[1] if len(sys.argv) > 1 else "schemas/reading.json"))
