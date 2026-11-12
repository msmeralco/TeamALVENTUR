"""Lambda entry point for the scheduled scoring job (EventBridge Scheduler)."""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from silip.ev.adapters import NeonEvStore
from silip.scoring.domain import LiveWeather, RunWeather, SimulatedWeatherInput
from silip.scoring.service import run_once
from silip.shared.config import ApiSettings, get_settings
from silip.shared.db import connect
from silip.shared.deps import get_data_source, get_score_store
from silip.weather.adapters import NeonWeatherStore, OpenMeteoClient, SimulatedWeather

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(UTC)


def run_weather(settings: ApiSettings) -> RunWeather:
    """WEATHER_SOURCE: simulated forecasts from data/sim, or Open-Meteo cached in Neon."""
    if settings.weather_source == "open_meteo":
        return LiveWeather(
            NeonWeatherStore(lambda: connect(settings)),
            OpenMeteoClient(settings.open_meteo_base_url),
        )
    return SimulatedWeatherInput(SimulatedWeather(settings.data_dir))


def ev_exposure(settings: ApiSettings) -> pd.DataFrame | None:
    """Stations near each transformer from the last EV load; None if it cannot be read."""
    try:
        return NeonEvStore(lambda: connect(settings)).exposure()
    except Exception as error:  # noqa: BLE001 - EV exposure is optional for a run
        logger.warning("no EV exposure for this run (%s)", type(error).__name__)
        return None


def handle(event: dict[str, Any], context: object) -> dict[str, Any]:
    """Score the latest interval. Returns {"status", "run_id", "transformers"}."""
    settings = get_settings()
    store = get_score_store(settings)
    if store is None:
        logger.warning("DATA_SOURCE=simulated has no score store; the API scores on request")
        return {"status": "skipped"}
    source = get_data_source(settings)
    result = run_once(
        source,
        store,
        settings.forecaster,
        settings.risk_scorer,
        utc_now,
        run_weather(settings),
        ev_exposure(settings),
    )
    logger.info(
        "scoring %s: run %s, %d transformers", result.status, result.run_id, result.transformers
    )
    return asdict(result)
