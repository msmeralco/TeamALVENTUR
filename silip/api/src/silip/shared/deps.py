"""FastAPI dependency that picks the DataSource strategy named by DATA_SOURCE."""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from silip.shared.config import ApiSettings, Settings, get_settings
from silip.shared.db import connect
from silip.shared.readings.adapters import ClampSource, SimulatedSource, SmartMeterSource
from silip.shared.readings.domain import DataSource

SOURCES: dict[str, Callable[[ApiSettings], DataSource]] = {
    "simulated": lambda settings: SimulatedSource(settings.data_dir),
    "clamp": lambda settings: ClampSource(lambda: connect(settings)),
    "smart_meter": lambda settings: SmartMeterSource(lambda: connect(settings)),
}


@lru_cache(maxsize=1)
def _source(name: str) -> DataSource:
    return SOURCES[name](get_settings())


def get_data_source(settings: Settings) -> DataSource:
    """One source per process, so the simulated CSVs load once."""
    return _source(settings.data_source)


Source = Annotated[DataSource, Depends(get_data_source)]
