"""Load the delivered EV files: `python -m silip.ev.load [data_dir] [--dry-run]` (default
ev_data_dir, `data/`).

Reads `evcs_locations.csv` and, when delivered, `ev_adoption.csv`, `evcs_stations_detail.csv`
and `evcs_plugs.csv` (contact columns are never read); joins stations to the transformers of
DATA_SOURCE. Writes to Neon unless DATA_SOURCE=simulated or `--dry-run` (then it only reports).
Never downloads or scrapes anything.
"""

from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime
from pathlib import Path

from silip.ev.adapters import NeonEvStore, load_from_files
from silip.shared.config import get_settings
from silip.shared.db import connect
from silip.shared.deps import get_data_source
from silip_ml.ev import EV_STATION_RADIUS_M


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(prog="silip.ev.load")
    parser.add_argument("data_dir", nargs="?", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="validate and report, write nothing")
    args = parser.parse_args()
    settings = get_settings()
    data_dir = args.data_dir or settings.ev_data_dir
    transformers = get_data_source(settings).transformers()
    load = load_from_files(data_dir, transformers, datetime.now(UTC))
    if args.dry_run:
        written = "no (--dry-run)"
    elif settings.data_source == "simulated":
        written = "no (DATA_SOURCE=simulated)"
    else:
        NeonEvStore(lambda: connect(settings)).write(load)
        written = "neon"
    exposed = int((load.exposure["stations_within"] > 0).sum())
    dc_exposed = int((load.exposure["dc_stations_within"].fillna(0) > 0).sum())
    print(
        f"rows_read={load.rows_read} dropped_outside_ph={load.dropped_outside_ph}"
        f" duplicates={load.duplicates} stations={len(load.stations)}"
        f" transformers={len(load.exposure)}"
        f" stations_with_detail={load.details_matched}"
        f" stations_without_detail={len(load.stations) - load.details_matched}"
        f" detail_rows_unmatched={load.details_unmatched} plugs={len(load.plugs)}"
        f" plugs_without_station={load.plugs_without_station}"
        f" transformers_with_station_within_{EV_STATION_RADIUS_M}m={exposed}"
        f" transformers_with_dc_within_{EV_STATION_RADIUS_M}m={dc_exposed}"
        f" adoption={load.adoption_status} adoption_rows={len(load.adoption)}"
        f" source_sha256={load.source_sha256[:12]}"
        f" exposure_sha256={load.exposure_sha256[:12]} written={written}"
    )


if __name__ == "__main__":
    main()
