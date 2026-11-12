"""Real building spots near each transformer site, from OpenStreetMap (© OSM contributors, ODbL 1.0).

The simulator puts each simulated household on one of these buildings so it lands on a real roof
on the map. Only the building's centre is kept, never its tags or address. The simulator reads the
committed snapshot only. Regenerate with:
    python -m silip_ml.readings.osm_buildings --out data/osm/buildings.csv
"""

from __future__ import annotations

import argparse
import json
import logging
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from silip_ml.readings.osm_transformers import (
    OVERPASS_URL,
    REQUEST_TIMEOUT_S,
    USER_AGENT,
    load_sites,
)

SNAPSHOT_PATH = Path("data/osm/buildings.csv")
COLUMNS = ["osm_node_id", "osm_way_id", "lat", "lon", "distance_m"]
SEARCH_RADIUS_M = 150
KEEP_PER_SITE = 80  # the simulator puts at most 60 homes on one transformer
METERS_PER_DEG_LAT = 111_320

log = logging.getLogger(__name__)


def query(site_ids: list[int]) -> str:
    """Overpass query: every building way within `SEARCH_RADIUS_M` of the given transformer nodes."""
    ids = ",".join(str(i) for i in site_ids)
    return f"""[out:json][timeout:180];
node(id:{ids})->.sites;
way["building"](around.sites:{SEARCH_RADIUS_M});
out center;"""


def distance_m(lat0: float, lon0: float, lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """Flat-earth distance in metres; fine at a few hundred metres."""
    dx = (lon - lon0) * METERS_PER_DEG_LAT * np.cos(np.radians(lat0))
    dy = (lat - lat0) * METERS_PER_DEG_LAT
    return np.hypot(dx, dy)


def to_snapshot(elements: list[dict], sites: pd.DataFrame) -> pd.DataFrame:
    """The `KEEP_PER_SITE` nearest buildings to each site, nearest first, one row per pair."""
    buildings = pd.DataFrame(
        [
            {"osm_way_id": e["id"], "lat": e["center"]["lat"], "lon": e["center"]["lon"]}
            for e in elements
            if e.get("type") == "way" and "center" in e
        ],
        columns=["osm_way_id", "lat", "lon"],
    ).drop_duplicates("osm_way_id")
    lat, lon = buildings["lat"].to_numpy(), buildings["lon"].to_numpy()
    frames = []
    for node_id, lat0, lon0 in zip(sites["osm_node_id"], sites["lat"], sites["lon"], strict=True):
        near = buildings.assign(distance_m=distance_m(float(lat0), float(lon0), lat, lon))
        near = near[near["distance_m"] <= SEARCH_RADIUS_M].nsmallest(KEEP_PER_SITE, "distance_m")
        frames.append(near.assign(osm_node_id=int(node_id)))
    snapshot = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=COLUMNS)
    snapshot["distance_m"] = snapshot["distance_m"].round(1)
    return snapshot[COLUMNS].sort_values(["osm_node_id", "distance_m"], ignore_index=True)


def load_buildings(path: Path = SNAPSHOT_PATH) -> pd.DataFrame:
    """Read the committed snapshot, or an empty frame if it is missing (households then scatter)."""
    if not path.exists():
        log.warning("%s not found; households will be scattered around their transformer", path)
        return pd.DataFrame(columns=COLUMNS)
    return pd.read_csv(path)


def fetch_elements(site_ids: list[int]) -> list[dict]:
    """POST the Overpass query once (a single large request; rerun by hand if the server is busy)."""
    body = urllib.parse.urlencode({"data": query(site_ids)}).encode()
    request = urllib.request.Request(  # noqa: S310 - fixed https URL
        OVERPASS_URL, data=body, headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as response:  # noqa: S310
        return json.load(response)["elements"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch buildings near transformer sites from OSM.")
    parser.add_argument("--out", type=Path, default=SNAPSHOT_PATH)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    sites = load_sites()
    elements = fetch_elements(sites["osm_node_id"].astype(int).tolist())
    snapshot = to_snapshot(elements, sites)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    snapshot.to_csv(args.out, index=False)
    print(
        f"OSM buildings: {len(elements)} raw, {snapshot['osm_way_id'].nunique()} kept "
        f"near {snapshot['osm_node_id'].nunique()} of {len(sites)} sites -> {args.out}"
    )


if __name__ == "__main__":
    main()
