"""The live demo story, end to end in fake time: simulator rig -> readings -> /demo snapshot."""

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from silip.app import app
from silip.bench.api import get_bench_readings
from silip.bench.domain import NotBenchError
from silip.bench.service import bench_snapshot, snapshot
from silip.bench.sim import Rig
from silip.shared.bench import config
from silip.shared.bench.domain import step_up

START = datetime(2026, 11, 12, 13, 0, tzinfo=UTC)


def _run(story: dict[int, tuple[str, bool]], ticks: int) -> tuple[pd.DataFrame, datetime]:
    """Tick the rig `ticks` times (2 s each), flipping switches at the given ticks."""
    rig, rows = Rig(), []
    for tick in range(ticks):
        if tick in story:
            rig.switches.set(*story[tick])
        now = START + timedelta(seconds=tick * config.SAMPLE_INTERVAL_S)
        rows += [payload for _, payload in rig.step(now)]
    frame = pd.DataFrame(rows)
    frame["ts"] = pd.to_datetime(frame["ts"])
    return frame, START + timedelta(seconds=ticks * config.SAMPLE_INTERVAL_S)


def _t1(frame: pd.DataFrame, now: datetime):
    return snapshot(frame, now).transformers[0]


def test_story_goes_ok_then_watch_then_critical_with_an_ev_reason():
    frame, now = _run({}, 15)
    assert _t1(frame, now).tier == "OK"
    frame, now = _run({10: ("heat", True)}, 25)
    assert _t1(frame, now).tier == "Watch"
    frame, now = _run({10: ("heat", True), 25: ("ev", True)}, 40)
    t1 = _t1(frame, now)
    assert t1.tier == "Critical"
    assert "House 3 added a large new load (likely EV)" in t1.reasons
    assert t1.homes_reporting == 4  # summed by SIN, house 4 included as the records say


def test_house_4_is_found_on_t2_by_its_voltage():
    frame, now = _run({10: ("heat", True), 25: ("ev", True), 45: ("ev", False)}, 60)
    flags = {f.home: f for f in snapshot(frame, now).fingerprints}
    assert flags["House 4"].mismatch and flags["House 4"].voltage_transformer == "BENCH-T2"
    assert not any(f.mismatch for home, f in flags.items() if home != "House 4")


def test_simulated_rows_are_labeled_replay():
    frame, now = _run({}, 10)
    result = snapshot(frame, now)
    assert result.mode == "replay" and result.is_simulated


class FakeReadings:
    def __init__(self, frame: pd.DataFrame) -> None:
        self.frame = frame

    def recent(self, since: datetime) -> pd.DataFrame:
        return self.frame[self.frame["ts"] > since]


def test_a_non_bench_transformer_is_refused():
    frame, now = _run({}, 5)
    with pytest.raises(NotBenchError):
        bench_snapshot(FakeReadings(frame), now, "T-106")
    app.dependency_overrides[get_bench_readings] = lambda: FakeReadings(frame)
    try:
        response = TestClient(app).get("/api/v1/bench/T-106")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 404


@pytest.mark.parametrize(
    ("series", "expected"),
    [
        ([0.6] * 6 + [2.6] * 6, 6),  # a real EV-like step that stays up
        ([0.6] * 6 + [2.6] * 2 + [0.6] * 4, None),  # a short spike
        (list(np.linspace(0.6, 2.6, 12)), None),  # a slow ramp
    ],
)
def test_step_detector(series, expected):
    assert step_up(np.array(series), config.EV_STEP_W, config.EV_HOLD_SAMPLES) == expected
