"""Simulate SILIP data. Output is always labeled is_simulated=True.

Usage: python sim/simulate.py --transformers 50 --days 30 --out data/sim
"""

import argparse
import hashlib
import os

import numpy as np
import pandas as pd

SALT = os.environ.get("SILIP_SIN_SALT", "dev-salt-change-me")


def sin_hash(raw: str) -> str:
    return hashlib.sha256((SALT + raw).encode()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--transformers", type=int, default=50)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--out", default="data/sim")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    os.makedirs(a.out, exist_ok=True)

    ts = pd.date_range("2026-04-01", periods=a.days * 96, freq="15min", tz="Asia/Manila")
    day = (ts.dayofyear - ts.dayofyear[0]).to_numpy()
    heat = 36 + 5 * np.sin(day / 4) + rng.normal(0, 1.5, len(ts))  # heat index, C
    hour = ts.hour.to_numpy() + ts.minute.to_numpy() / 60
    evening = ((hour >= 18) | (hour < 0.5)).astype(float)

    tx_rows, sin_rows, load_rows = [], [], []
    for t in range(a.transformers):
        tid = f"T-{100 + t}"
        rated = rng.choice([25, 37.5, 50, 75, 100])
        homes = int(rng.integers(20, 61))
        tx_rows.append({"transformer_id": tid, "rated_kva": rated, "homes": homes, "is_simulated": True})
        total = np.zeros(len(ts))
        for h in range(homes):
            sh = sin_hash(f"{tid}-{h}")
            sin_rows.append({"sin_hash": sh, "transformer_id": tid, "has_clamp": bool(rng.random() < 0.6), "is_simulated": True})
            base = rng.uniform(0.2, 0.6)
            ac = evening * rng.uniform(0.8, 1.6) * np.clip((heat - 30) / 10, 0, 1.5)
            total += base + ac + rng.normal(0, 0.05, len(ts))
        if rng.random() < 0.2:  # an EV appears mid-run
            start = int(rng.integers(len(ts) // 3, 2 * len(ts) // 3))
            ev = ((hour >= 20) | (hour < 1)).astype(float) * rng.uniform(3.3, 7.4)
            ev[:start] = 0
            total += ev
        load_rows.append(pd.DataFrame({"transformer_id": tid, "ts": ts, "transformer_kw": total,
                                       "load_pct": total / (rated * 0.9), "heat_index_c": heat, "is_simulated": True}))

    pd.DataFrame(tx_rows).to_csv(f"{a.out}/transformers.csv", index=False)
    pd.DataFrame(sin_rows).to_csv(f"{a.out}/sin_map.csv", index=False)
    pd.concat(load_rows).to_csv(f"{a.out}/transformer_load_15m.csv", index=False)
    print(f"Simulated {a.transformers} transformers x {a.days} days -> {a.out}")


if __name__ == "__main__":
    main()
