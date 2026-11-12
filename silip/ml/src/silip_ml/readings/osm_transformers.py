"""Real distribution-transformer sites from OpenStreetMap (© OpenStreetMap contributors, ODbL 1.0).

The simulator reads the committed snapshot only; it never calls the network. Regenerate with:
    python -m silip_ml.readings.osm_transformers --out data/osm/transformers.csv
"""

from __future__ import annotations

import argparse
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

SNAPSHOT_PATH = Path("data/osm/transformers.csv")
COLUMNS = ["osm_node_id", "lat", "lon", "operator", "power", "transformer"]
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "silip-dev/0.1"
# Metro Manila and nearby Meralco franchise area: south, west, north, east.
BBOX = "14.35,120.90,14.80,121.15"
QUERY = f"""[out:json][timeout:60];
(
  node["power"="transformer"]({BBOX});
  node["power"="pole"]["transformer"]({BBOX});
);
out body;"""
MERALCO_WIKIDATA = "Q6817918"
REQUEST_TIMEOUT_S = 120
RETRIES, FIRST_BACKOFF_S = 5, 10
BUSY_CODES = {429, 502, 503, 504}  # the public Overpass server sheds load with these

log = logging.getLogger(__name__)


class NotEnoughSitesError(ValueError):
    """More transformers were requested than the OSM snapshot has sites."""


def is_meralco_distribution(tags: dict[str, str]) -> bool:
    """Meralco-operated, or tagged as a distribution transformer with no other operator."""
    if tags.get("transformer", "distribution") != "distribution":
        return False  # substation mains, traction, generator step-up
    operator = tags.get("operator", "")
    if "meralco" in operator.lower() or tags.get("operator:wikidata") == MERALCO_WIKIDATA:
        return True
    return tags.get("transformer") == "distribution" and not operator


def to_snapshot(elements: list[dict]) -> pd.DataFrame:
    """Keep plausible Meralco distribution transformers, one row per OSM node."""
    rows = [
        {
            "osm_node_id": element["id"],
            "lat": element["lat"],
            "lon": element["lon"],
            "operator": element.get("tags", {}).get("operator", ""),
            "power": element.get("tags", {}).get("power", ""),
            "transformer": element.get("tags", {}).get("transformer", ""),
        }
        for element in elements
        if is_meralco_distribution(element.get("tags", {}))
    ]
    return pd.DataFrame(rows, columns=COLUMNS).sort_values("osm_node_id", ignore_index=True)


def load_sites(path: Path = SNAPSHOT_PATH) -> pd.DataFrame:
    """Read the committed snapshot.

    Raises:
        FileNotFoundError: if the snapshot is missing.
        ValueError: if a column is missing.
    """
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; it is committed under data/osm/")
    sites = pd.read_csv(path, keep_default_na=False)
    missing = set(COLUMNS) - set(sites.columns)
    if missing:
        raise ValueError(f"{path} lacks columns {sorted(missing)}")
    return sites


def sample_sites(sites: pd.DataFrame, count: int, seed: int) -> pd.DataFrame:
    """Pick `count` distinct sites, the same ones for the same seed.

    Raises:
        NotEnoughSitesError: if `count` exceeds the number of sites.
    """
    if count > len(sites):
        raise NotEnoughSitesError(f"asked for {count} transformers; snapshot has {len(sites)}")
    picks = np.random.default_rng(seed).choice(len(sites), size=count, replace=False)
    return sites.iloc[picks].reset_index(drop=True)


def fetch_elements() -> list[dict]:
    """POST the Overpass query, retrying with backoff while the public server is busy."""
    body = urllib.parse.urlencode({"data": QUERY}).encode()
    request = urllib.request.Request(  # noqa: S310 - fixed https URL
        OVERPASS_URL, data=body, headers={"User-Agent": USER_AGENT}
    )
    wait_s = FIRST_BACKOFF_S
    for attempt in range(1, RETRIES + 1):
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as response:  # noqa: S310
                return json.load(response)["elements"]
        except (urllib.error.HTTPError, TimeoutError) as error:
            busy = not isinstance(error, urllib.error.HTTPError) or error.code in BUSY_CODES
            if attempt == RETRIES or not busy:
                raise
            log.warning("Overpass attempt %d failed (%s); retrying in %d s", attempt, error, wait_s)
            time.sleep(wait_s)
            wait_s *= 2
    raise AssertionError("unreachable")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Meralco transformer sites from OSM.")
    parser.add_argument("--out", type=Path, default=SNAPSHOT_PATH)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    elements = fetch_elements()
    snapshot = to_snapshot(elements)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    snapshot.to_csv(args.out, index=False)
    print(f"OSM nodes: {len(elements)} raw, {len(snapshot)} kept -> {args.out}")


if __name__ == "__main__":
    main()
