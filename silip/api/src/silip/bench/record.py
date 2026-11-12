"""Record a bench run from the database, for Replay. Works however the readings arrived.

python -m silip.bench.record --minutes 3 --out capture.jsonl
python -m silip.bench.sim --replay capture.jsonl --http https://<api-origin>
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

from silip.shared.bench import config
from silip.shared.bench.adapters import NeonBenchReadings
from silip.shared.config import get_settings
from silip.shared.db import connect

SECONDS_PER_HOUR = 3600


def to_lines(readings: pd.DataFrame) -> list[dict]:
    """One replay line per reading: offset in seconds, the device, and its payload."""
    clamps = {home.sin_hash: home.clamp_id for home in config.HOMES}
    readings = readings[readings["sin_hash"].isin(list(clamps))].sort_values("ts")
    if readings.empty:
        return []
    start = readings["ts"].min()
    lines = []
    for row in readings.to_dict("records"):
        power_kw = float(row["power_kw"])
        lines.append(
            {
                "t": round((row["ts"] - start).total_seconds(), 3),
                "clamp_id": clamps[row["sin_hash"]],
                "payload": {
                    "sin_hash": row["sin_hash"],
                    "transformer_id": row["transformer_id"],
                    "ts": row["ts"].isoformat(),
                    "voltage_v": float(row["voltage_v"]),
                    "current_a": power_kw * 1000 / row["voltage_v"] if row["voltage_v"] else 0.0,
                    "power_kw": power_kw,
                    "power_factor": 1.0,
                    "energy_kwh_interval": power_kw * config.SAMPLE_INTERVAL_S / SECONDS_PER_HOUR,
                    "event": None if pd.isna(row["event"]) else row["event"],
                    "is_simulated": True,  # anything replayed is simulated
                },
            }
        )
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Save the last few minutes of the bench rig")
    parser.add_argument("--minutes", type=float, default=3)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    reader = NeonBenchReadings(lambda: connect(get_settings()))
    readings = reader.recent(datetime.now(UTC) - timedelta(minutes=args.minutes))
    readings["ts"] = pd.to_datetime(readings["ts"], utc=True)
    lines = to_lines(readings)
    args.out.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    print(f"recorded {len(lines)} readings to {args.out}")


if __name__ == "__main__":
    main()
