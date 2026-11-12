"""Engineer-only EV routes: DOE chargers on the map and the delivered adoption statistics."""

from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends

from silip.ev import service
from silip.ev.adapters import STATIONS_CSV, MemoryEvStore, NeonEvStore, load_from_files
from silip.ev.domain import STATION_SOURCE, Adoption, ChargerMap, EvStore
from silip.shared.auth.api import AUTH_RESPONSES, Engineer
from silip.shared.config import Settings
from silip.shared.db import connect
from silip.shared.deps import Source
from silip.shared.geo import BoundingBox, parse_bbox
from silip.shared.readings.domain import DataSource
from silip_ml.ev import EV_STATION_RADIUS_M

router = APIRouter(prefix="/api/v1/ev", tags=["ev"])


@lru_cache(maxsize=4)
def _memory(data_dir: Path, source: DataSource) -> MemoryEvStore:
    """EV_SOURCE=csv: one loader pass per process over the delivered files."""
    if not (data_dir / STATIONS_CSV).exists():
        return MemoryEvStore()
    return MemoryEvStore(load_from_files(data_dir, source.transformers(), datetime.now(UTC)))


def get_ev_store(settings: Settings, source: Source) -> EvStore:
    """What `silip.ev.load` wrote to Neon, whatever DATA_SOURCE is (EV data is real); in memory
    from the files only when no database is configured (EV_SOURCE=csv)."""
    if settings.ev_store == "csv":
        return _memory(settings.ev_data_dir, source)
    return NeonEvStore(lambda: connect(settings))


Ev = Annotated[EvStore, Depends(get_ev_store)]
Bbox = Annotated[BoundingBox | None, Depends(parse_bbox)]


@router.get("/chargers", response_model=ChargerMap, responses=AUTH_RESPONSES)
def ev_chargers(_: Engineer, ev: Ev, box: Bbox) -> ChargerMap:
    """Public DOE charging stations in view (real sites, not homes)."""
    return ChargerMap(
        radius_m=EV_STATION_RADIUS_M,
        source=STATION_SOURCE,
        stations=service.chargers(ev.stations(), box),
        is_simulated=False,
    )


@router.get("/adoption", response_model=Adoption, responses=AUTH_RESPONSES)
def ev_adoption(_: Engineer, ev: Ev) -> Adoption:
    """EV adoption statistics as delivered; `not_loaded` until the file arrives."""
    return service.adoption(ev.adoption())
