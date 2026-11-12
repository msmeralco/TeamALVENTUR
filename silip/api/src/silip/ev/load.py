"""Load the delivered EV files: `python -m silip.ev.load [data_dir]` (default ev_data_dir, `data/`).

Reads `evcs_locations.csv` and, when delivered, `ev_adoption.csv`; joins stations to the
transformers of DATA_SOURCE. Writes to Neon unless DATA_SOURCE=simulated (then it only reports).
Never downloads or scrapes anything.
"""

from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from silip.ev.adapters import NeonEvStore, load_from_files
from silip.shared.config import get_settings
from silip.shared.db import connect
from silip.shared.deps import get_data_source
from silip_ml.ev import EV_STATION_RADIUS_M


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings = get_settings()
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else settings.ev_data_dir
    transformers = get_data_source(settings).transformers()
    load = load_from_files(data_dir, transformers, datetime.now(UTC))
    if settings.data_source == "simulated":
        written = "no (DATA_SOURCE=simulated)"
    else:
        NeonEvStore(lambda: connect(settings)).write(load)
        written = "neon"
    exposed = int((load.exposure["stations_within"] > 0).sum())
    print(
        f"rows_read={load.rows_read} dropped_outside_ph={load.dropped_outside_ph}"
        f" duplicates={load.duplicates} stations={len(load.stations)}"
        f" transformers={len(load.exposure)}"
        f" transformers_with_station_within_{EV_STATION_RADIUS_M}m={exposed}"
        f" adoption={load.adoption_status} adoption_rows={len(load.adoption)}"
        f" source_sha256={load.source_sha256[:12]} written={written}"
    )


if __name__ == "__main__":
    main()
