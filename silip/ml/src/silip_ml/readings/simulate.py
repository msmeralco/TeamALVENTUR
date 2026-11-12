"""Simulate SILIP data. Every row is labeled is_simulated=True.

Recipe: the silip-domain skill. Usage:
    python -m silip_ml.readings.simulate --transformers 50 --days 30 --out data/sim
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from silip_ml.core.config import get_ml_settings
from silip_ml.core.privacy import sin_hash
from silip_ml.readings.aggregate import sum_by_transformer
from silip_ml.readings.dataset import FILES
from silip_ml.readings.domain import INTERVAL, STEPS_PER_DAY, load_pct

RATINGS_KVA = [25, 37.5, 50, 75, 100]
CLAMP_SHARE = 0.6
EV_SHARE = 0.2
# Simulated area: a box around Metro Manila, only to place pins on a map.
CENTER_LAT, CENTER_LON, SPREAD_DEG = 14.58, 121.0, 0.05
# Trip rule from silip-domain: load >110% for 3+ h on 3+ days.
TRIP_LOAD_PCT, TRIP_MIN_STEPS, TRIP_MIN_DAYS = 1.10, 12, 3
OTHER_OUTAGES_PER_DAY = 0.05
MEDIAN_DURATION_MIN = {"overload": 180, "weather": 150, "equipment": 240}
DURATION_SIGMA = 0.5
GASP_JITTER_DEG, REPORT_JITTER_DEG = 0.0003, 0.0015


def _homes_kw(
    rng: np.random.Generator, homes: int, heat: np.ndarray, hour: np.ndarray
) -> np.ndarray:
    evening = ((hour >= 18) | (hour < 0.5)).astype(float)
    base = rng.uniform(0.2, 0.6, (homes, 1))
    aircon = evening * rng.uniform(0.8, 1.6, (homes, 1)) * np.clip((heat - 30) / 10, 0, 1.5)
    return base + aircon + rng.normal(0, 0.05, (homes, len(heat)))


def _trip_start(ts: pd.DatetimeIndex, pct: np.ndarray) -> pd.Timestamp | None:
    over = pd.Series(pct > TRIP_LOAD_PCT).rolling(TRIP_MIN_STEPS).min().fillna(0).astype(bool)
    flagged_days = pd.Series(ts[over.to_numpy()].normalize()).drop_duplicates()
    if len(flagged_days) < TRIP_MIN_DAYS:
        return None
    third_day = flagged_days.iloc[TRIP_MIN_DAYS - 1]
    return ts[over.to_numpy() & (ts.normalize() == third_day)][0]


def _signals(rng: np.random.Generator, outage: dict, clamped: int) -> list[dict]:
    rows = []
    for _ in range(clamped):
        rows.append({"kind": "last_gasp", "seconds": rng.uniform(0, 60), "jitter": GASP_JITTER_DEG})
    for _ in range(1 + rng.poisson(3)):
        rows.append(
            {"kind": "report", "seconds": rng.exponential(600), "jitter": REPORT_JITTER_DEG}
        )
    return [
        {
            "outage_id": outage["outage_id"],
            "kind": row["kind"],
            "ts": outage["start_ts"] + pd.Timedelta(seconds=row["seconds"]),
            "lat": outage["lat"] + rng.normal(0, row["jitter"]),
            "lon": outage["lon"] + rng.normal(0, row["jitter"]),
            "is_simulated": True,
        }
        for row in rows
    ]


def simulate(transformers: int, days: int, seed: int, salt: str) -> dict[str, pd.DataFrame]:
    """Build every table in memory. Keys match `silip_ml.readings.dataset.FILES`."""
    rng = np.random.default_rng(seed)
    ts = pd.date_range("2026-04-01", periods=days * STEPS_PER_DAY, freq=INTERVAL, tz="Asia/Manila")
    day = (ts.day_of_year - ts.day_of_year[0]).to_numpy()
    heat = 36 + 5 * np.sin(day / 4) + rng.normal(0, 1.5, len(ts))  # heat index, C
    hour = ts.hour.to_numpy() + ts.minute.to_numpy() / 60

    tx_rows, sin_rows, load_frames, outage_rows, signal_rows, household_frames = (
        [],
        [],
        [],
        [],
        [],
        [],
    )
    for t in range(transformers):
        tid = f"T-{100 + t}"
        rated = float(rng.choice(RATINGS_KVA))
        homes = int(rng.integers(20, 61))
        lat, lon = (
            CENTER_LAT + rng.uniform(-1, 1) * SPREAD_DEG,
            CENTER_LON + rng.uniform(-1, 1) * SPREAD_DEG,
        )
        hashes = [sin_hash(f"{tid}-{h}", salt) for h in range(homes)]
        has_clamp = rng.random(homes) < CLAMP_SHARE
        kw = _homes_kw(rng, homes, heat, hour)
        if rng.random() < EV_SHARE:  # one home adds an EV mid-run, charging from 8 PM
            start = int(rng.integers(len(ts) // 3, 2 * len(ts) // 3))
            ev = ((hour >= 20) | (hour < 1)).astype(float) * rng.uniform(3.3, 7.4)
            ev[:start] = 0
            kw[int(rng.integers(homes))] += ev

        readings = pd.DataFrame(
            {
                "sin_hash": np.repeat(hashes, len(ts)),
                "transformer_id": tid,
                "ts": ts[np.tile(np.arange(len(ts)), homes)],  # keeps the time zone
                "power_kw": kw.ravel(),
            }
        )
        total = sum_by_transformer(readings)["measured_kw"].to_numpy()
        pct = load_pct(total, rated)
        load_frames.append(
            pd.DataFrame(
                {
                    "transformer_id": tid,
                    "ts": ts,
                    "transformer_kw": total,
                    "load_pct": pct,
                    "heat_index_c": heat,
                }
            )
        )
        tx_rows.append(
            {
                "transformer_id": tid,
                "rated_kva": rated,
                "homes": homes,
                "coverage_pct": has_clamp.mean(),
                "lat": lat,
                "lon": lon,
            }
        )
        sin_rows += [
            {"sin_hash": h, "transformer_id": tid, "has_clamp": bool(c)}
            for h, c in zip(hashes, has_clamp, strict=True)
        ]
        if t == 0:  # per-home detail for one transformer, for the household view
            household_frames.append(readings[np.repeat(has_clamp, len(ts))])

        starts: list[tuple[pd.Timestamp, str]] = []
        if (trip := _trip_start(ts, pct)) is not None:
            starts.append((trip, "overload"))
        for _ in range(rng.poisson(days * OTHER_OUTAGES_PER_DAY)):
            starts.append(
                (ts[int(rng.integers(len(ts)))], str(rng.choice(["weather", "equipment"])))
            )
        for start, cause in starts:
            outage = {
                "outage_id": f"O-{len(outage_rows) + 1:04d}",
                "transformer_id": tid,
                "start_ts": start,
                "cause": cause,
                "duration_min": round(
                    float(rng.lognormal(np.log(MEDIAN_DURATION_MIN[cause]), DURATION_SIGMA))
                ),
                "lat": lat,
                "lon": lon,
            }
            outage_rows.append(outage)
            signal_rows += _signals(rng, outage, int(has_clamp.sum()))

    tables = {
        "transformers": pd.DataFrame(tx_rows),
        "sin_map": pd.DataFrame(sin_rows),
        "load": pd.concat(load_frames, ignore_index=True),
        "outages": pd.DataFrame(outage_rows),
        "signals": pd.DataFrame(signal_rows),
        "households": pd.concat(household_frames, ignore_index=True),
    }
    return {name: frame.assign(is_simulated=True) for name, frame in tables.items()}


def write(tables: dict[str, pd.DataFrame], out: Path) -> None:
    """Write each table as CSV under `out`."""
    out.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        frame.to_csv(out / FILES.get(name, f"{name}.csv"), index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate SILIP data (is_simulated=True).")
    parser.add_argument("--transformers", type=int, default=50)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--out", type=Path, default=Path("data/sim"))
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    tables = simulate(args.transformers, args.days, args.seed, get_ml_settings().sin_salt)
    write(tables, args.out)
    print(
        f"Simulated {args.transformers} transformers x {args.days} days, "
        f"{len(tables['outages'])} outages -> {args.out}"
    )


if __name__ == "__main__":
    main()
