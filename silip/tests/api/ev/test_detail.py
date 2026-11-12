"""DOE station detail and plugs: join to stations, exposure fields, EV source, no contact fields."""

import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest
from pydantic import SecretStr

from silip.ev.adapters import INSERT_PLUG, INSERT_STATION, _records, load_from_files
from silip.ev.domain import STATION_COLUMNS
from silip.shared.config import ApiSettings
from tests.api.conftest import FIXTURE_EV
from tests.api.helpers import auth

ENGINEER = auth("engineer-token")
NOW = datetime(2026, 11, 13, tzinfo=UTC)
TRANSFORMERS = pd.DataFrame(
    {
        "transformer_id": ["T-hub", "T-far"],
        "lat": [14.3652, 10.0],  # ~22 m from Test Hub Near T-100
        "lon": [121.0175, 125.0],
        "is_simulated": [True, True],
    }
)
CONTACT = re.compile(
    r"contact|email|e-mail|street_view|serial|@|www\.|https?://example\.com"
    r"|(\+?63|0)9?\d{2}[ -]?\d{3,4}[ -]?\d{4}",
    re.IGNORECASE,
)


def test_detail_joins_stations_and_plugs() -> None:
    load = load_from_files(FIXTURE_EV, TRANSFORMERS, NOW)
    stations = load.stations.set_index("name").to_dict("index")
    near = stations["Test Hub Near T-100"]

    assert load.details_matched == 2 and load.details_unmatched == 1
    assert load.plugs_without_station == 1
    assert (near["classification"], near["n_ac"], near["n_dc"]) == ("CUCS", 1, 1)
    assert near["max_capacity_kw"] == 60.0
    assert (near["price_min_php_kwh"], near["price_max_php_kwh"]) == (25.0, 31.0)
    assert pd.isna(stations["Test Hub Far"]["doe_station_number"])
    plugs = load.plugs.to_dict("records")
    assert sorted(load.plugs["plug_id"]) == [
        "CCS Combo 2 - Plug 1 #1",
        "Type 2 - Plug 1 #1",
        "Type 2 - Plug 1 #1",
        "Type 2 - Plug 1 #2",
    ]
    dc = next(plug for plug in plugs if plug["plug_id"] == "CCS Combo 2 - Plug 1 #1")
    assert dc["status"] == "out_of_service"
    assert pd.isna(dc["price_php_kwh"])  # a PHP service fee, not PHP/kWh
    assert not load.plugs["is_simulated"].any()


def test_exposure_counts_dc_and_largest_capacity() -> None:
    load = load_from_files(FIXTURE_EV, TRANSFORMERS, NOW)
    by_id = load.exposure.set_index("transformer_id").to_dict("index")

    assert by_id["T-hub"]["dc_stations_within"] == 1
    assert by_id["T-hub"]["max_capacity_kw_within"] == 60.0
    assert by_id["T-far"]["dc_stations_within"] == 0
    assert pd.isna(by_id["T-far"]["max_capacity_kw_within"])
    assert load.exposure_sha256 != load.source_sha256  # covers the detail files too


def test_without_detail_files_fields_are_null(tmp_path: Path) -> None:
    shutil.copy(FIXTURE_EV / "evcs_locations.csv", tmp_path)

    load = load_from_files(tmp_path, TRANSFORMERS, NOW)

    assert load.stations["doe_station_number"].isna().all() and load.plugs.empty
    assert load.exposure["dc_stations_within"].isna().all()
    assert load.exposure_sha256 == load.source_sha256


def test_neon_rows_are_plain_python_and_sql_updates_only_detail() -> None:
    load = load_from_files(FIXTURE_EV, TRANSFORMERS, NOW)
    row = _records(load.stations, STATION_COLUMNS)[0]

    assert all(isinstance(v, str | int | float | datetime | None) for v in row.values()), row
    update = INSERT_STATION.split("DO UPDATE SET ")[1]
    assert "name" not in update and "source_sha256" not in update and "n_dc" in update
    assert INSERT_PLUG.endswith("DO NOTHING")


def test_ev_source_defaults_to_neon_when_a_database_is_configured() -> None:
    url = SecretStr("postgresql://db.example/x")
    assert ApiSettings(_env_file=None, database_url=url).ev_store == "neon"  # type: ignore[call-arg]
    assert ApiSettings(_env_file=None, database_secret_arn="arn").ev_store == "neon"  # type: ignore[call-arg]
    assert ApiSettings(_env_file=None, database_url=url, ev_source="csv").ev_store == "csv"  # type: ignore[call-arg]


def test_ev_source_is_csv_without_a_database(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("DATABASE_URL", "DATABASE_POOLER_URL", "DATABASE_SECRET_ARN"):
        monkeypatch.delenv(name, raising=False)
    assert ApiSettings(_env_file=None).ev_store == "csv"  # type: ignore[call-arg]


def test_api_returns_detail_and_no_contact_fields(client) -> None:
    chargers = client.get("/api/v1/ev/chargers", headers=ENGINEER)
    card = client.get("/api/v1/transformers/T-100", headers=ENGINEER)
    assert chargers.status_code == card.status_code == 200

    near = next(s for s in chargers.json()["stations"] if s["name"] == "Test Hub Near T-100")
    assert (near["classification"], near["n_ac"], near["n_dc"], near["n_plugs"]) == (
        "CUCS",
        1,
        1,
        2,
    )
    assert near["max_capacity_kw"] == 60.0 and near["price_max_php_kwh"] == 31.0
    ev = card.json()["ev"]
    assert ev["dc_stations_within"] == 1 and ev["max_capacity_kw_within"] == 60.0
    assert ev["stations"][0]["classification"] == "CUCS"
    for payload in (chargers.json(), ev):
        text = json.dumps(payload)
        assert not CONTACT.search(text), CONTACT.search(text)
