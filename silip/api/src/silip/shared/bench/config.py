"""The bench rig ("mini barangay on the table") in one place. Rig-scale values, in watts.

The simulator, the live rule, the API and docs/demo read these. They are starting points chosen so
the 2-minute story reads clearly (OK, then Watch on the heat wave, then Critical on the EV); match
them to the built rig here and nowhere else. [VERIFY] each against the rig once it is wired.
"""

from __future__ import annotations

from dataclasses import dataclass

from silip_ml.core.privacy import sin_hash
from silip_ml.readings.domain import ASSUMED_POWER_FACTOR

BENCH_PREFIX = "BENCH-"  # the only transformers the public /demo routes will serve
# Mock households only. Not a secret: it makes stable, obviously fake hashes for the rig.
DEMO_SALT = "silip-bench-demo"

# Timing. The firmware DEMO build publishes at the same interval.
SAMPLE_INTERVAL_S = 2.0
# The /demo page reads the last 3 minutes: enough for the 2-minute fingerprint window and an EV
# step that is still on, and a third of the rows a 10-minute window would move every 2 s.
WINDOW_S = 180

# Electrical model (simulator). AC or DC is not decided yet: see docs/demo/hardware.md.
SOURCE_V = 12.0  # [VERIFY] rig supply voltage
SERIES_OHMS = 2.0  # per transformer, so its bus visibly sags under load [VERIFY]
HOUSE_WIRE_OHMS = 0.1  # drop to each house, so homes on one transformer differ slightly
VOLTAGE_NOISE_V = 0.005  # measurement noise
BASE_W = 0.6  # each LED house at rest
HEAT_WAVE_W = 0.5  # "Heat wave" switch: extra load in every house (aircon)
EV_W = 2.0  # "EV" switch: heavy load on house 3
FLICKER_W = 0.05  # small appliance turning on and off, so each home moves on its own
FLICKER_CHANCE = 0.08  # chance per sample that a home's small appliance toggles
REPLAY_SPEED = 1.0


@dataclass(frozen=True)
class BenchTransformer:
    transformer_id: str
    rated_w: float
    lat: float
    lon: float

    @property
    def rated_kva(self) -> float:
        """The `transformer.rated_kva` column, so `load_pct` works unchanged at rig scale."""
        return self.rated_w / (ASSUMED_POWER_FACTOR * 1000)


@dataclass(frozen=True)
class BenchHome:
    label: str
    clamp_id: str  # the device's ID in the HTTPS ingest URL
    mock_sin: str  # obviously fake; only its salted hash leaves this module
    record_transformer: str  # what the records say (the node is configured with this)
    wired_transformer: str  # where it is really connected

    @property
    def sin_hash(self) -> str:
        return sin_hash(self.mock_sin, DEMO_SALT)


# Where the rig sits on the map. [VERIFY] set to the venue.
BENCH_LAT, BENCH_LON = 14.4445, 120.9939
# T1 rating. Measured in the dry run (after voltage sag): 4 homes at rest = 55%, heat wave = 92%
# to 97% (Watch), plus EV = about 135% (Critical). Flicker moves T1 by under 5%, so it never tips
# the heat wave into Critical or drops it below Watch.
TRANSFORMERS = (
    BenchTransformer("BENCH-T1", rated_w=4.4, lat=BENCH_LAT, lon=BENCH_LON),
    BenchTransformer("BENCH-T2", rated_w=2.4, lat=BENCH_LAT + 0.0004, lon=BENCH_LON + 0.0004),
)
EV_HOME = "House 3"
HOMES = (
    BenchHome("House 1", "bench-house-1", "MOCK-HOUSE-1", "BENCH-T1", "BENCH-T1"),
    BenchHome("House 2", "bench-house-2", "MOCK-HOUSE-2", "BENCH-T1", "BENCH-T1"),
    BenchHome("House 3", "bench-house-3", "MOCK-HOUSE-3", "BENCH-T1", "BENCH-T1"),
    # The records error the demo uncovers: listed under T1, wired to T2.
    BenchHome("House 4", "bench-house-4", "MOCK-HOUSE-4", "BENCH-T1", "BENCH-T2"),
    BenchHome("House 5", "bench-house-5", "MOCK-HOUSE-5", "BENCH-T2", "BENCH-T2"),
)

# Live rule. The 24 h forecast model needs weeks of history, so the bench uses load now vs
# rating. It keeps the baseline's meaning ("over 100% of rating, held") but compresses time:
# HOLD_SAMPLES (6 s) stands in for the baseline's 2 h.
HOLD_SAMPLES = 3
# EV: power steps up by this much and stays up. Above heat wave (0.5 W) and flicker (0.05 W).
EV_STEP_W = 1.2
EV_HOLD_SAMPLES = 3
# Last gasp: this many homes on one transformer, within this window, opens an outage.
LAST_GASP_MIN_HOMES = 2
LAST_GASP_WINDOW_S = 10
# Voltage fingerprinting (silip_ml.readings.fingerprint).
FINGERPRINT_WINDOW_S = 120
FINGERPRINT_MIN_LOAD_SWING_W = 0.3  # below this, a transformer's load tells us nothing
FINGERPRINT_MIN_CONFIDENCE = 0.95  # flag only when the voltage match clearly beats the runner-up
FINGERPRINT_MIN_SAMPLES = 20  # 40 s of aligned samples


def is_bench(transformer_id: str) -> bool:
    return transformer_id.startswith(BENCH_PREFIX)


def home_by_hash() -> dict[str, BenchHome]:
    return {home.sin_hash: home for home in HOMES}
