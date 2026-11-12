"""Score the latest load interval once and store it; a failure is recorded and re-raised.

Weather comes first. A weather failure (provider, cache insert or read) never fails a run: the
run records the status and scores with what it has.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

import pandas as pd

from silip.dashboard.service import assess
from silip.scoring.domain import (
    Clock,
    LiveWeather,
    RunResult,
    RunWeather,
    SimulatedWeatherInput,
)
from silip.shared.readings.domain import DataSource
from silip.shared.scores.domain import DuplicateRunError, ScoreRun, ScoreStore
from silip.weather.domain import WeatherOutlook
from silip.weather.service import cells_for, no_forecast, outlook, refresh

logger = logging.getLogger(__name__)


def _inputs_simulated(source: DataSource) -> bool:
    """Label a failed run like its inputs; when they cannot be read, assume simulated."""
    try:
        return bool(source.transformers()["is_simulated"].any())
    except Exception:  # noqa: BLE001 - labeling must not mask the original failure
        return True


def run_weather(
    weather: RunWeather | None, source: DataSource, as_of: datetime, now: datetime
) -> WeatherOutlook:
    """The forecast this run uses. Never raises: any failure is logged and reads as missing."""
    if weather is None:
        return no_forecast()
    try:
        match weather:
            case SimulatedWeatherInput(reader=reader):
                return outlook(reader, as_of)
            case LiveWeather(store=store, fetcher=fetcher):
                try:
                    return refresh(cells_for(source.transformers()), now, fetcher, store)
                except Exception as error:  # noqa: BLE001 - e.g. the Neon insert failed
                    logger.warning(
                        "weather refresh failed (%s); reading the cache", type(error).__name__
                    )
                    return outlook(store, now)
    except Exception as error:  # noqa: BLE001 - a weather failure never fails a run
        logger.warning("no weather for this run (%s)", type(error).__name__)
    return no_forecast()


def run_once(
    source: DataSource,
    store: ScoreStore,
    forecaster: str,
    risk_scorer: str,
    clock: Clock,
    weather: RunWeather | None = None,
    ev_exposure: pd.DataFrame | None = None,
) -> RunResult:
    """Idempotent per 15-minute data interval and strategy pair."""
    latest = source.latest_load_ts()
    if latest is None:
        logger.info("no load data yet; nothing to score")
        return RunResult("skipped", None, 0)
    as_of = latest.to_pydatetime()
    if store.has_complete_run(as_of, forecaster, risk_scorer):
        logger.info("interval %s already scored; skipping", as_of.isoformat())
        return RunResult("skipped", None, 0)
    run_id, started_at = str(uuid.uuid4()), clock()
    forecast_weather = run_weather(weather, source, as_of, started_at)
    try:
        assessed = assess(source, latest, forecaster, risk_scorer, forecast_weather, ev_exposure)
        forecaster = assessed.forecaster
        run = ScoreRun(
            run_id=run_id,
            as_of=as_of,
            started_at=started_at,
            finished_at=clock(),
            forecaster=forecaster,
            risk_scorer=risk_scorer,
            transformers=len(assessed.scores),
            is_simulated=any(score.is_simulated for score in assessed.scores),
            weather_issued_at=forecast_weather.issued_at,
            weather_status=forecast_weather.status,
        )
        store.write_run(run, assessed.scores, assessed.forecast, assessed.details)
    except DuplicateRunError:
        logger.info("interval %s scored by a parallel run; skipping", as_of.isoformat())
        return RunResult("skipped", None, 0)
    except Exception as error:
        failed = ScoreRun(
            run_id,
            as_of,
            started_at,
            clock(),
            forecaster,
            risk_scorer,
            0,
            is_simulated=_inputs_simulated(source),
            weather_issued_at=forecast_weather.issued_at,
            weather_status=forecast_weather.status,
        )
        store.write_failed(failed, type(error).__name__)
        raise
    return RunResult("complete", run_id, run.transformers)
