"""What one scheduled scoring run reports, and where its weather comes from."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from silip.shared.scores.domain import SCORING_WINDOW
from silip.weather.domain import WeatherFetcher, WeatherReader, WeatherStore

__all__ = [
    "SCORING_WINDOW",
    "Clock",
    "LiveWeather",
    "RunResult",
    "RunWeather",
    "SimulatedWeatherInput",
]

Clock = Callable[[], datetime]  # timezone-aware now(); injected so tests control time


@dataclass(frozen=True)
class RunResult:
    """`skipped` when there is no load yet or this interval already has a complete run."""

    status: Literal["complete", "skipped"]
    run_id: str | None
    transformers: int


@dataclass(frozen=True)
class SimulatedWeatherInput:
    """Simulated forecasts (data/sim), read on the data's own clock; never fetched."""

    reader: WeatherReader


@dataclass(frozen=True)
class LiveWeather:
    """Open-Meteo, refreshed at most hourly into the Neon cache."""

    store: WeatherStore
    fetcher: WeatherFetcher


RunWeather = SimulatedWeatherInput | LiveWeather
