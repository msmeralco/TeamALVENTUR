import numpy as np
import pandas as pd

from silip_ml.readings.fingerprint import fingerprint

SOURCE_V, OHMS = 12.0, 0.5
SETTINGS = {"min_load_swing": 0.5, "min_confidence": 0.95, "min_samples": 20}


def _loads(seed: int, swing: bool) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = 120
    index = pd.date_range("2026-11-12 21:00", periods=n, freq="2s", tz="Asia/Manila")
    if not swing:
        return pd.DataFrame({"T1": np.full(n, 2.0), "T2": np.full(n, 1.5)}, index=index)
    # Independent on/off steps on each transformer (heat wave on T1 and T2, EV on T1).
    t1 = 1.5 + 1.0 * (np.arange(n) >= 40) + 1.5 * (np.arange(n) >= 80) + rng.normal(0, 0.05, n)
    t2 = 1.2 + 0.8 * ((np.arange(n) // 25) % 2) + rng.normal(0, 0.05, n)
    return pd.DataFrame({"T1": t1, "T2": t2}, index=index)


def _voltages(loads: pd.DataFrame, wiring: dict[str, str], seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            home: SOURCE_V - OHMS * loads[t] + rng.normal(0, 0.01, len(loads))
            for home, t in wiring.items()
        },
        index=loads.index,
    )


def test_correct_wiring_matches_the_records():
    loads = _loads(1, swing=True)
    wiring = {"House 1": "T1", "House 5": "T2"}
    result = fingerprint(_voltages(loads, wiring, 2), loads, wiring, **SETTINGS)
    assert [(r.home, r.voltage_transformer, r.mismatch) for r in result] == [
        ("House 1", "T1", False),
        ("House 5", "T2", False),
    ]


def test_swapped_wiring_is_flagged_with_confidence():
    loads = _loads(3, swing=True)
    records = {"House 4": "T1"}
    voltages = _voltages(loads, {"House 4": "T2"}, 4)  # really on T2
    [house4] = fingerprint(voltages, loads, records, **SETTINGS)
    assert house4.mismatch and house4.voltage_transformer == "T2"
    assert house4.confidence > 0.5
    assert house4.explanation == "Voltage dips with T2, not T1."


def test_too_little_load_swing_does_not_decide():
    loads = _loads(5, swing=False)
    [house4] = fingerprint(
        _voltages(loads, {"House 4": "T2"}, 6), loads, {"House 4": "T1"}, **SETTINGS
    )
    assert house4.voltage_transformer is None and not house4.mismatch
