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
from silip_ml.readings.osm_buildings import SEARCH_RADIUS_M, load_buildings
from silip_ml.readings.osm_buildings import SNAPSHOT_PATH as BUILDINGS_PATH
from silip_ml.readings.osm_transformers import SNAPSHOT_PATH, load_sites, sample_sites

RATINGS_KVA = [25, 37.5, 50, 75, 100]
CLAMP_SHARE = 0.6
EV_SHARE = 0.2
# Trip rule from silip-domain: load >110% for 3+ h on 3+ days.
TRIP_LOAD_PCT, TRIP_MIN_STEPS, TRIP_MIN_DAYS = 1.10, 12, 3
OTHER_OUTAGES_PER_DAY = 0.05
MEDIAN_DURATION_MIN = {"overload": 180, "weather": 150, "equipment": 240}
DURATION_SIGMA = 0.5
GASP_JITTER_DEG, REPORT_JITTER_DEG = 0.0003, 0.0015
# Clamps: SCT-013-000 per docs/SPEC.md#hardware; IDs follow the firmware's MQTT client ID.
CT_MODEL = "SCT-013-000"
CLAMP_ID = "silip-node-{:04d}"
INSTALL_WINDOW_DAYS = 120  # clamps went in up to this long before the run starts
OFFLINE_SHARE = 0.05  # clamps that stopped reporting before the run ended
SHARED_UNIT_JITTER_M = 4  # homes sharing one building (multi-unit) sit a few metres apart
METERS_PER_DEG_LAT = 111_320


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


def _place_homes(
    rng: np.random.Generator,
    homes: int,
    lat: float,
    lon: float,
    near: pd.DataFrame,
    taken: set[int],
) -> pd.DataFrame:
    """One spot per home: the nearest free OSM buildings, shared as units when there are too few.

    Without any building nearby, homes scatter within `SEARCH_RADIUS_M` (osm_way_id stays empty).
    """
    free = near[~near["osm_way_id"].isin(taken)]
    pool = free if len(free) > 0 else near
    if len(pool) == 0:
        radius = SEARCH_RADIUS_M * np.sqrt(rng.random(homes))
        angle = rng.uniform(0, 2 * np.pi, homes)
        dy, dx = radius * np.sin(angle), radius * np.cos(angle)
        way = pd.Series([pd.NA] * homes, dtype="Int64")
        base_lat, base_lon = np.full(homes, lat), np.full(homes, lon)
    else:
        picks = pool.iloc[np.arange(homes) % len(pool)]  # nearest first, then units share
        taken.update(picks["osm_way_id"].astype(int))
        shared = np.arange(homes) >= len(pool)
        dy, dx = (rng.normal(0, SHARED_UNIT_JITTER_M, (2, homes)) * shared).astype(float)
        way = picks["osm_way_id"].astype("Int64").reset_index(drop=True)
        base_lat, base_lon = picks["lat"].to_numpy(), picks["lon"].to_numpy()
    k_lon = METERS_PER_DEG_LAT * np.cos(np.radians(lat))
    return pd.DataFrame(
        {"lat": base_lat + dy / METERS_PER_DEG_LAT, "lon": base_lon + dx / k_lon, "osm_way_id": way}
    )


def _clamps(
    rng: np.random.Generator, hashes: list[str], first_id: int, ts: pd.DatetimeIndex
) -> list[dict]:
    """One clamp per opted-in home: install date before the run, last report near its end."""
    rows = []
    for i, h in enumerate(hashes):
        installed = ts[0] - pd.Timedelta(days=float(rng.uniform(1, INSTALL_WINDOW_DAYS)))
        offline = rng.random() < OFFLINE_SHARE
        gap_min = rng.uniform(60, 3 * 24 * 60) if offline else rng.uniform(0, 15)
        rows.append(
            {
                "clamp_id": CLAMP_ID.format(first_id + i),
                "sin_hash": h,
                "ct_model": CT_MODEL,
                "installed_at": installed.floor("min"),
                "last_seen_at": (ts[-1] - pd.Timedelta(minutes=float(gap_min))).floor("s"),
            }
        )
    return rows


def simulate(
    transformers: int,
    days: int,
    seed: int,
    salt: str,
    sites_path: Path = SNAPSHOT_PATH,
    buildings_path: Path = BUILDINGS_PATH,
) -> dict[str, pd.DataFrame]:
    """Build every table in memory. Keys match `silip_ml.readings.dataset.FILES`.

    Transformer positions are real OSM sites (`sites_path`) and homes sit on real OSM buildings
    near them (`buildings_path`); load, homes, clamps and outages are simulated.

    Raises:
        NotEnoughSitesError: if `transformers` exceeds the sites in the snapshot.
    """
    sites = sample_sites(load_sites(sites_path), transformers, seed)
    buildings = load_buildings(buildings_path)
    rng = np.random.default_rng(seed)
    # A separate stream, so adding homes' places and clamps leaves every load number unchanged.
    place_rng = np.random.default_rng([seed, 1])
    taken: set[int] = set()
    clamp_rows: list[dict] = []
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
        site = sites.iloc[t]
        lat, lon = float(site["lat"]), float(site["lon"])
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
                "osm_node_id": int(site["osm_node_id"]),
            }
        )
        near = buildings[buildings["osm_node_id"] == site["osm_node_id"]]
        places = _place_homes(place_rng, homes, lat, lon, near, taken)
        sin_rows += [
            {"sin_hash": h, "transformer_id": tid, "has_clamp": bool(c), **place}
            for h, c, place in zip(hashes, has_clamp, places.to_dict("records"), strict=True)
        ]
        clamped = [h for h, c in zip(hashes, has_clamp, strict=True) if c]
        clamp_rows += _clamps(place_rng, clamped, len(clamp_rows) + 1, ts)
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
        "clamps": pd.DataFrame(clamp_rows),
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
