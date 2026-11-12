"""EV loader: delivered header to snake_case, bounding-box drop, dedupe, optional adoption file."""

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from silip.ev.adapters import MemoryEvStore, file_sha256, load_from_files
from silip_ml.ev import EV_STATION_RADIUS_M, exposure, haversine_m, station_id

NOW = datetime(2026, 11, 13, tzinfo=UTC)
HEADER = "EVCS Establishment,Region,Province,City/Municipality,Barangay,Latitude,Longitude\n"
ROWS = [
    "Hub A,NCR,Metro Manila,Makati,Poblacion,14.5650,121.0300",
    "Hub A,NCR,Metro Manila,Makati,Poblacion,14.5650,121.0300",  # exact duplicate
    "Hub B,REGION VI,Negros Occidental,Bacolod City,Taculing,10.6568,122.9523",
    "Swapped,NCR,Metro Manila,Makati,Poblacion,121.0300,14.5650",  # outside the Philippines
    "Zero,NCR,Metro Manila,Makati,Poblacion,0,0",
]
TRANSFORMERS = pd.DataFrame(
    {
        "transformer_id": ["T-near", "T-far"],
        "lat": [14.5700, 14.7000],  # ~560 m and ~15 km from Hub A
        "lon": [121.0300, 121.0300],
        "is_simulated": [True, True],
    }
)
ADOPTION = pd.DataFrame(
    {
        "period": ["2025"],
        "geography_level": ["country"],
        "geography": ["PH"],
        "metric": ["ev_sales"],
        "vehicle_class": ["all"],
        "value": [100],
        "unit": ["vehicles"],
        "source_url": ["https://example.org/report"],
        "retrieved_at": ["2026-11-01T00:00:00Z"],
        "is_simulated": [True],
    }
)


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    (tmp_path / "evcs_locations.csv").write_text(HEADER + "\n".join(ROWS) + "\n", encoding="utf-8")
    return tmp_path


def test_maps_header_drops_outside_and_dedupes(data_dir: Path) -> None:
    load = load_from_files(data_dir, TRANSFORMERS, NOW)

    assert load.rows_read == 5
    assert load.dropped_outside_ph == 2
    assert load.duplicates == 1
    assert sorted(load.stations["name"]) == ["Hub A", "Hub B"]
    hub_b = load.stations[load.stations["name"] == "Hub B"].iloc[0].to_dict()
    assert (hub_b["city"], hub_b["barangay"]) == ("Bacolod City", "Taculing")
    assert hub_b["station_id"] == station_id("Hub B", 10.6568, 122.9523)
    assert len(hub_b["station_id"]) == 16
    assert set(load.stations["source_sha256"]) == {file_sha256(data_dir / "evcs_locations.csv")}
    assert not load.stations["is_simulated"].any()


def test_missing_adoption_file_is_not_loaded(data_dir: Path) -> None:
    load = load_from_files(data_dir, TRANSFORMERS, NOW)

    assert load.adoption_status == "not_loaded"
    assert load.adoption.empty
    assert MemoryEvStore(load).adoption().empty


def test_adoption_file_loads(data_dir: Path) -> None:
    ADOPTION.to_csv(data_dir / "ev_adoption.csv", index=False)

    load = load_from_files(data_dir, TRANSFORMERS, NOW)

    assert load.adoption_status == "loaded"
    assert load.adoption["value"].tolist() == [100]


def test_adoption_rejects_unknown_metric(data_dir: Path) -> None:
    ADOPTION.assign(metric="ev_guess").to_csv(data_dir / "ev_adoption.csv", index=False)

    with pytest.raises(ValueError, match="unknown metrics"):
        load_from_files(data_dir, TRANSFORMERS, NOW)


def test_missing_station_column_is_refused(tmp_path: Path) -> None:
    (tmp_path / "evcs_locations.csv").write_text("Name,Latitude,Longitude\nX,14.5,121\n")

    with pytest.raises(ValueError, match="missing columns"):
        load_from_files(tmp_path, TRANSFORMERS, NOW)


def test_exposure_counts_stations_within_radius(data_dir: Path) -> None:
    load = load_from_files(data_dir, TRANSFORMERS, NOW)
    by_id = load.exposure.set_index("transformer_id")

    assert by_id.loc["T-near", "stations_within"] == 1
    assert by_id.loc["T-far", "stations_within"] == 0
    assert by_id.loc["T-near", "nearest_station_m"] == pytest.approx(556, abs=5)
    assert set(by_id["radius_m"]) == {EV_STATION_RADIUS_M}
    assert by_id["is_simulated"].all()  # simulated transformers make the exposure simulated


def test_exposure_without_stations() -> None:
    stations = pd.DataFrame({"lat": [], "lon": []})

    joined = exposure(TRANSFORMERS, stations)

    assert joined["stations_within"].tolist() == [0, 0]
    assert joined["nearest_station_m"].isna().all()


def test_haversine_one_degree_of_latitude() -> None:
    distance = haversine_m(np.array([0.0]), np.array([0.0]), np.array([1.0]), np.array([0.0]))

    assert distance[0, 0] == pytest.approx(111_195, rel=1e-3)
