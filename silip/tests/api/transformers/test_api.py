from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pandas as pd
import pytest

from silip.app import app
from silip.scoring.service import run_once
from silip.shared.deps import get_data_source, get_score_store
from silip.shared.readings.adapters import SimulatedSource
from silip.transformers.api import SCORE_TTL, utc_now
from silip.transformers.domain import TransformerDataUnavailableError
from silip.transformers.service import CARD_HISTORY, compute_risk, risk_map, transformer_card
from silip_ml.core.registry import UnknownStrategyError
from tests.api.helpers import FakeScoreStore, StepClock, auth

START = datetime(2026, 1, 1, tzinfo=UTC)
LATER = START + timedelta(days=1)


def test_risk_map_is_engineer_only(client):
    assert client.get("/api/v1/transformers").status_code == 401
    assert client.get("/api/v1/transformers", headers=auth("household-token")).status_code == 403


def test_risk_map_lists_every_transformer_critical_first(client, dataset):
    body = client.get("/api/v1/transformers", headers=auth("engineer-token")).json()
    assert len(body) == len(dataset.transformers)
    order = {"Critical": 0, "Watch": 1, "OK": 2}
    tiers = [order[item["risk"]["tier"]] for item in body]
    assert tiers == sorted(tiers)
    assert all(item["is_simulated"] and item["risk"]["is_simulated"] for item in body)


def test_bbox_filters_and_rejects_bad_input(client):
    empty = client.get("/api/v1/transformers?bbox=0,0,1,1", headers=auth("engineer-token"))
    assert empty.json() == []
    bad = client.get("/api/v1/transformers?bbox=1,2,3", headers=auth("engineer-token"))
    assert bad.status_code == 422


def test_card_has_history_and_forecast(client, dataset):
    transformer_id = dataset.transformers["transformer_id"].iloc[0]
    card = client.get(
        f"/api/v1/transformers/{transformer_id}", headers=auth("engineer-token")
    ).json()
    kinds = {point["is_forecast"] for point in card["load"]}
    assert kinds == {True, False}
    assert (
        client.get("/api/v1/transformers/T-NOPE", headers=auth("engineer-token")).status_code == 404
    )


@pytest.fixture
def overrides():
    """Per-test dependency overrides on top of the session client's, restored afterwards."""
    saved = dict(app.dependency_overrides)
    yield app.dependency_overrides
    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved)


class CountingSource(SimulatedSource):
    """Counts scoring computations (each one reads the latest interval once)."""

    def __init__(self, data_dir) -> None:
        super().__init__(data_dir)
        self.computations = 0

    def latest_load_ts(self) -> pd.Timestamp | None:
        self.computations += 1
        return super().latest_load_ts()


def test_reads_the_latest_completed_run_from_the_store(client, overrides, sim_dir):
    source, store = SimulatedSource(sim_dir), FakeScoreStore()
    run_once(source, store, "seasonal_naive", "rules", StepClock(START))
    newer = run_once(source, store, "seasonal_naive", "lightgbm", StepClock(LATER))
    with pytest.raises(UnknownStrategyError):  # a failed run must not hide the newer one
        run_once(source, store, "seasonal_naive", "nope", StepClock(LATER + timedelta(hours=1)))
    overrides[get_score_store] = lambda: store

    body = client.get("/api/v1/transformers", headers=auth("engineer-token")).json()

    latest = store.latest_run()
    assert latest is not None and latest.run.run_id == newer.run_id
    stored = {s.transformer_id: s.model_dump(mode="json") for s in latest.scores}
    assert {item["transformer_id"]: item["risk"] for item in body} == stored
    assert {item["scored_at"] for item in body} == {
        latest.run.finished_at.isoformat().replace("+00:00", "Z")
    }
    transformer_id = body[0]["transformer_id"]
    card = client.get(f"/api/v1/transformers/{transformer_id}", headers=auth("engineer-token"))
    forecast = [p for p in card.json()["load"] if p["is_forecast"]]
    mine = latest.forecast[latest.forecast["transformer_id"] == transformer_id]
    assert [p["kw"] for p in forecast] == pytest.approx(list(mine["kw_pred"]))
    history = [p for p in card.json()["load"] if not p["is_forecast"]]
    assert len(history) == CARD_HISTORY / pd.Timedelta(minutes=15)


def test_no_completed_run_is_503(client, overrides):
    overrides[get_score_store] = FakeScoreStore
    response = client.get("/api/v1/transformers", headers=auth("engineer-token"))
    assert response.status_code == 503
    assert response.json()["detail"] == "No completed scoring run yet"


def test_simulated_mode_recomputes_after_the_ttl(client, overrides, sim_dir):
    source, now = CountingSource(sim_dir), [START]
    overrides[get_data_source] = lambda: source
    overrides[utc_now] = lambda: now[0]

    def get() -> list[dict]:
        return client.get("/api/v1/transformers", headers=auth("engineer-token")).json()

    first = get()
    now[0] = START + SCORE_TTL - timedelta(seconds=1)
    get()
    assert source.computations == 1
    now[0] = START + SCORE_TTL
    get()
    assert source.computations == 2
    assert {item["scored_at"] for item in first} == {"2026-01-01T00:00:00Z"}


def test_transformer_without_a_week_of_readings_is_omitted_until_forecastable(dataset, sim_dir):
    transformers = dataset.transformers.copy()
    added = transformers.iloc[0].copy()
    added["transformer_id"] = "T-150"
    transformers = pd.concat([transformers, added.to_frame().T], ignore_index=True)
    one_reading = dataset.load.iloc[[0]].copy()
    one_reading["transformer_id"] = "T-150"
    one_reading["ts"] = dataset.load["ts"].max()
    load = pd.concat([dataset.load, one_reading], ignore_index=True)
    real = SimulatedSource(sim_dir)
    source = SimpleNamespace(
        transformers=lambda: transformers,
        load=lambda since=None: load if since is None else load[load["ts"] > since],
        latest_load_ts=lambda: load["ts"].max(),
        outages=real.outages,
        clamp_counts=real.clamp_counts,
    )

    snapshot = compute_risk(source, "seasonal_naive", "rules", START)

    assert "T-150" not in {item.transformer_id for item in risk_map(snapshot, source, None)}
    assert len(risk_map(snapshot, source, None)) == len(dataset.transformers)
    with pytest.raises(TransformerDataUnavailableError):
        transformer_card(snapshot, source, "T-150")
