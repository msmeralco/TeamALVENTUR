"""API test client on simulated data with a fake Cognito decoder (no network)."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from silip.app import app
from silip.shared.auth.api import token_decoder
from silip.shared.config import ApiSettings, get_settings
from silip.shared.deps import get_data_source
from silip.shared.readings.adapters import SimulatedSource
from tests.api.helpers import CLIENT_ID, FakeDecoder


@pytest.fixture(scope="session")
def client(sim_dir) -> Iterator[TestClient]:
    settings = ApiSettings(
        data_dir=sim_dir,
        data_source="simulated",
        cognito_user_pool_id="pool",
        cognito_client_id=CLIENT_ID,
        auth_disabled=False,
    )
    source = SimulatedSource(sim_dir)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_data_source] = lambda: source
    app.dependency_overrides[token_decoder] = FakeDecoder
    yield TestClient(app)
    app.dependency_overrides.clear()
