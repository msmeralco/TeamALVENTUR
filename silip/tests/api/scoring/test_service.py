"""The scheduled scoring run: writes once per interval, records failures, labels simulated data."""

from datetime import UTC, datetime

import pandas as pd
import pytest

from silip.dashboard.domain import ACTIONS
from silip.scoring import handler
from silip.scoring.domain import LiveWeather, SimulatedWeatherInput
from silip.scoring.service import run_once
from silip.shared.config import ApiSettings
from silip.shared.readings.adapters import SimulatedSource
from silip.weather.adapters import SimulatedWeather
from silip.weather.domain import WeatherFetchError
from silip_ml.core.registry import UnknownStrategyError
from silip_ml.readings.domain import STEPS_PER_DAY
from tests.api.helpers import FakeScoreStore, StepClock

START = datetime(2026, 1, 1, tzinfo=UTC)


class MarkedSource(SimulatedSource):
    """Real (non-simulated) transformer rows, with one load row of `marked` flagged simulated."""

    def __init__(self, data_dir, marked: str) -> None:
        super().__init__(data_dir)
        self._marked = marked

    def transformers(self) -> pd.DataFrame:
        return super().transformers().assign(is_simulated=False)

    def load(self, since=None) -> pd.DataFrame:
        load = super().load(since).assign(is_simulated=False)
        first = load.index[load["transformer_id"] == self._marked][-1]
        load.loc[first, "is_simulated"] = True
        return load


def test_a_run_writes_every_transformer_and_its_forecast(sim_dir, dataset):
    store = FakeScoreStore()
    result = run_once(SimulatedSource(sim_dir), store, "seasonal_naive", "rules", StepClock(START))

    assert result.status == "complete"
    stored = store.latest_run()
    assert stored is not None and stored.run.run_id == result.run_id
    count = len(dataset.transformers)
    assert result.transformers == stored.run.transformers == len(stored.scores) == count
    assert len(stored.forecast) == count * STEPS_PER_DAY
    assert stored.run.as_of == dataset.load["ts"].max()
    assert stored.run.is_simulated and stored.forecast["is_simulated"].all()
    assert stored.run.started_at < stored.run.finished_at


def test_a_second_run_for_the_same_interval_is_skipped(sim_dir):
    store = FakeScoreStore()
    source = SimulatedSource(sim_dir)
    run_once(source, store, "seasonal_naive", "rules", StepClock(START))

    again = run_once(source, store, "seasonal_naive", "rules", StepClock(START))

    assert again.status == "skipped" and again.run_id is None
    assert len(store.complete) == 1


def test_a_failed_run_is_recorded_and_keeps_the_previous_run(sim_dir):
    store = FakeScoreStore()
    source = SimulatedSource(sim_dir)
    first = run_once(source, store, "seasonal_naive", "rules", StepClock(START))

    with pytest.raises(UnknownStrategyError):
        run_once(source, store, "seasonal_naive", "no-such-scorer", StepClock(START))

    [(failed, error_class)] = store.failed
    assert error_class == "UnknownStrategyError" and failed.transformers == 0
    assert failed.is_simulated  # labeled like its inputs
    latest = store.latest_run()
    assert latest is not None and latest.run.run_id == first.run_id


def test_is_simulated_comes_from_the_inputs(sim_dir, dataset):
    marked = str(dataset.transformers["transformer_id"].iloc[0])
    store = FakeScoreStore()
    run_once(MarkedSource(sim_dir, marked), store, "seasonal_naive", "rules", StepClock(START))

    stored = store.latest_run()
    assert stored is not None
    flags = {score.transformer_id: score.is_simulated for score in stored.scores}
    assert flags.pop(marked) is True
    assert not any(flags.values())
    assert stored.run.is_simulated
    by_transformer = stored.forecast.groupby("transformer_id")["is_simulated"].all()
    assert by_transformer[marked] and not by_transformer.drop(marked).any()


def test_handler_skips_in_simulated_mode(monkeypatch, sim_dir):
    settings = ApiSettings(data_source="simulated", data_dir=sim_dir)
    monkeypatch.setattr(handler, "get_settings", lambda: settings)
    assert handler.handle({}, None) == {"status": "skipped"}


class RaceStore(FakeScoreStore):
    """A parallel run stores the same interval between our check and our write."""

    def has_complete_run(self, as_of: datetime, forecaster: str, risk_scorer: str) -> bool:
        return False


def test_losing_a_race_for_the_same_interval_is_a_skip_not_a_failure(sim_dir):
    store = RaceStore()
    source = SimulatedSource(sim_dir)
    run_once(source, store, "seasonal_naive", "rules", StepClock(START))

    again = run_once(source, store, "seasonal_naive", "rules", StepClock(START))

    assert again.status == "skipped" and store.failed == [] and len(store.complete) == 1


class FailingFetcher:
    def fetch(self, cells):
        raise WeatherFetchError("provider down")


class BrokenStore:
    """A weather cache whose reads and inserts both fail (Neon unreachable)."""

    def latest(self, as_of):
        raise OSError("neon unreachable")

    def insert(self, rows):
        raise OSError("neon unreachable")


class InsertFails(SimulatedWeather):
    """Stored simulated forecasts readable, but the insert after a fetch fails."""

    def insert(self, rows):
        raise OSError("insert refused")


class OkFetcher:
    def __init__(self):
        self.calls = 0

    def fetch(self, cells):
        self.calls += 1
        return pd.DataFrame(
            columns=[
                "cell_id",
                "lat",
                "lon",
                "ts",
                "temperature_c",
                "relative_humidity_pct",
                "precipitation_mm",
            ]
        )


def test_a_run_stores_dashboard_details_and_the_weather_it_used(sim_dir, dataset):
    store = FakeScoreStore()
    weather = SimulatedWeatherInput(SimulatedWeather(sim_dir))
    run_once(SimulatedSource(sim_dir), store, "seasonal_naive", "rules", StepClock(START), weather)

    stored = store.latest_run()
    assert stored is not None
    assert stored.run.weather_status in {"fresh", "stale"}
    assert stored.run.weather_issued_at is not None
    assert len(stored.details) == len(dataset.transformers)
    for detail in stored.details:
        assert detail.action in ACTIONS and detail.peak_ts is not None
        assert detail.drivers and detail.drivers[0].feature == "peak_load_pct"
        assert detail.clamps_online is not None and detail.clamps_installed is not None


@pytest.mark.parametrize(
    "weather",
    [
        LiveWeather(BrokenStore(), FailingFetcher()),
        LiveWeather(BrokenStore(), OkFetcher()),
    ],
    ids=["provider and cache down", "cache insert fails"],
)
def test_a_weather_failure_never_fails_the_run(sim_dir, weather):
    store = FakeScoreStore()
    result = run_once(
        SimulatedSource(sim_dir), store, "seasonal_naive", "rules", StepClock(START), weather
    )

    assert result.status == "complete" and store.failed == []
    stored = store.latest_run()
    assert stored is not None and stored.run.weather_status == "missing"
    assert stored.run.weather_issued_at is None


def test_a_failed_insert_falls_back_to_the_stored_forecast(sim_dir, dataset):
    store, fetcher = FakeScoreStore(), OkFetcher()
    latest = dataset.load["ts"].max().to_pydatetime()
    weather = LiveWeather(InsertFails(sim_dir), fetcher)
    run_once(SimulatedSource(sim_dir), store, "seasonal_naive", "rules", lambda: latest, weather)

    stored = store.latest_run()
    assert stored is not None and fetcher.calls == 1
    assert stored.run.weather_status in {"fresh", "stale"}  # the cached simulated forecast


def test_without_weather_a_weather_forecaster_falls_back_to_its_twin(sim_dir):
    store = FakeScoreStore()
    run_once(
        SimulatedSource(sim_dir),
        store,
        "lightgbm_weather",
        "rules",
        StepClock(START),
        LiveWeather(BrokenStore(), FailingFetcher()),
    )

    stored = store.latest_run()
    assert stored is not None and stored.run.forecaster == "lightgbm"
