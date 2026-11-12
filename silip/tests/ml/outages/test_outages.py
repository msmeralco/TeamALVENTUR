import pytest

from silip_ml.core.registry import create, names
from silip_ml.outages.domain import haversine_m


@pytest.mark.parametrize("name", names("outage_locator"))
def test_locator_pins_every_outage_near_its_transformer(dataset, name):
    pins = create("outage_locator", name).locate(dataset.signals)
    assert set(pins["outage_id"]) == set(dataset.outages["outage_id"])
    joined = pins.merge(dataset.outages, on="outage_id", suffixes=("", "_true"))
    errors = haversine_m(joined["lat"], joined["lon"], joined["lat_true"], joined["lon_true"])
    assert (errors < 2_000).all()  # simulated reports scatter about 165 m


@pytest.mark.parametrize("name", names("eta_estimator"))
def test_eta_ranges_are_ordered(dataset, name):
    estimates = create("eta_estimator", name).fit(dataset.outages).predict(dataset.outages)
    assert len(estimates) == len(dataset.outages)
    assert (estimates["eta_p10_min"] <= estimates["eta_p50_min"]).all()
    assert (estimates["eta_p50_min"] <= estimates["eta_p90_min"]).all()


def test_haversine_one_degree_latitude_is_about_111_km():
    assert 110_000 < haversine_m(0.0, 0.0, 1.0, 0.0) < 112_000
