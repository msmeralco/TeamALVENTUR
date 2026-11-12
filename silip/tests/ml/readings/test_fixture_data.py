"""Checks on the data notebooks/00_generate_mock_data.ipynb writes (its `test` scale)."""

import pandas as pd

from silip_ml.readings.osm_transformers import load_sites
from tests.conftest import FIXTURE_SIM


def _csv(name: str) -> pd.DataFrame:
    return pd.read_csv(FIXTURE_SIM / name)


def test_every_row_is_simulated_and_sins_are_hashes():
    for path in FIXTURE_SIM.glob("*.csv"):
        assert pd.read_csv(path, usecols=["is_simulated"])["is_simulated"].all(), path.name
    sins = _csv("sin_map.csv")["sin_hash"]
    assert sins.str.fullmatch(r"[0-9a-f]{64}").all()  # salted SHA-256, never a raw SIN


def test_transformers_sit_on_committed_osm_sites():
    placed = _csv("transformers.csv").merge(load_sites(), on="osm_node_id", suffixes=("", "_osm"))
    assert len(placed) == len(_csv("transformers.csv"))
    assert (placed["lat"] == placed["lat_osm"]).all() and (placed["lon"] == placed["lon_osm"]).all()


def test_each_clamped_home_has_exactly_one_clamp():
    homes, clamps = _csv("sin_map.csv"), _csv("clamps.csv")
    assert set(clamps["sin_hash"]) == set(homes.loc[homes["has_clamp"], "sin_hash"])
    assert clamps["sin_hash"].is_unique and clamps["clamp_id"].str.match(r"silip-node-\d{4}").all()
    installed = pd.to_datetime(clamps["installed_at"], format="ISO8601")
    assert (installed <= pd.to_datetime(clamps["last_seen_at"], format="ISO8601")).all()


def test_load_has_gaps_only_where_no_clamp_reported():
    load = _csv("transformer_load_15m.csv")
    assert (load["homes_reporting"] > 0).all()
    assert not load.duplicated(["transformer_id", "ts"]).any()
