"""Engineer-only weather outlook, and the dependencies other routes use to read the forecast."""

from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends

from silip.shared.auth.api import AUTH_RESPONSES, Engineer
from silip.shared.config import Settings
from silip.shared.db import connect
from silip.shared.deps import Source
from silip.shared.geo import BoundingBox, parse_bbox, within
from silip.weather.adapters import NeonWeatherStore, SimulatedWeather
from silip.weather.domain import (
    LIVE_ON_SIMULATED_NOTE,
    SOURCE_LABELS,
    AreaOutlook,
    WeatherOutlook,
    WeatherReader,
)
from silip.weather.service import area_hours, cell_peaks, cells_for, outlook

router = APIRouter(prefix="/api/v1/weather", tags=["weather"])


@lru_cache(maxsize=4)
def _simulated(data_dir: Path) -> SimulatedWeather:
    return SimulatedWeather(data_dir)  # reads the CSV once per process


def get_weather_reader(settings: Settings) -> WeatherReader:
    """WEATHER_SOURCE=open_meteo reads the Neon cache the scoring job fills; else data/sim."""
    if settings.weather_source == "open_meteo":
        return NeonWeatherStore(lambda: connect(settings))
    return _simulated(settings.data_dir)


Reader = Annotated[WeatherReader, Depends(get_weather_reader)]


def weather_now(settings: Settings, source: Source) -> datetime:
    """The time the forecast is judged at: the data's own clock for simulated weather, the wall
    clock for Open-Meteo (the live next 48 h, even beside simulated load)."""
    if settings.weather_source == "simulated":
        latest = source.latest_load_ts()
        if latest is not None:
            return latest.to_pydatetime()
    return datetime.now(UTC)


Now = Annotated[datetime, Depends(weather_now)]


def current_outlook(reader: Reader, now: Now) -> WeatherOutlook:
    return outlook(reader, now)


Forecast = Annotated[WeatherOutlook, Depends(current_outlook)]
Bbox = Annotated[BoundingBox | None, Depends(parse_bbox)]


@router.get("/outlook", response_model=AreaOutlook, responses=AUTH_RESPONSES)
def weather_outlook(
    _: Engineer, forecast: Forecast, now: Now, source: Source, settings: Settings, box: Bbox
) -> AreaOutlook:
    """The next 48 h of heat index and rain over the transformers in view, hour by hour."""
    transformers = within(source.transformers(), box)
    cells = cells_for(transformers) if not transformers.empty else []
    live_on_simulated = settings.weather_source == "open_meteo" and bool(
        source.transformers()["is_simulated"].any()
    )
    return AreaOutlook(
        issued_at=forecast.issued_at,
        status=forecast.status,
        source=SOURCE_LABELS[settings.weather_source],
        hours=area_hours(forecast, cells, now),
        cells=cell_peaks(forecast, cells, now),
        is_simulated=forecast.is_simulated or settings.weather_source == "simulated",
        note=LIVE_ON_SIMULATED_NOTE if live_on_simulated else None,
    )
