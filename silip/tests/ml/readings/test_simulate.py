import subprocess
import sys

import pandas as pd
import pytest

from silip_ml.readings.osm_transformers import NotEnoughSitesError, load_sites
from silip_ml.readings.simulate import simulate


def test_simulator_outputs_labeled_and_hashed(tmp_path):
    out = tmp_path / "sim"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "silip_ml.readings.simulate",
            "--transformers",
            "3",
            "--days",
            "2",
            "--out",
            str(out),
        ],
        check=True,
    )
    sins = pd.read_csv(out / "sin_map.csv")
    load = pd.read_csv(out / "transformer_load_15m.csv")
    assert sins["is_simulated"].all() and load["is_simulated"].all()
    assert sins["sin_hash"].str.len().eq(64).all()  # SHA-256 hex, never raw SINs
    assert len(load) == 3 * 2 * 96


def _sites(tmp_path, count: int):
    sites = pd.DataFrame(
        {
            "osm_node_id": range(1, count + 1),
            "lat": [14.4 + i / 100 for i in range(count)],
            "lon": [121.0 + i / 100 for i in range(count)],
            "operator": "Meralco",
            "power": "pole",
            "transformer": "distribution",
        }
    )
    path = tmp_path / "sites.csv"
    sites.to_csv(path, index=False)
    return sites, path


def test_simulated_transformers_sit_on_snapshot_sites(tmp_path):
    sites, path = _sites(tmp_path, 5)
    first = simulate(transformers=3, days=1, seed=4, salt="s", sites_path=path)["transformers"]
    again = simulate(transformers=3, days=1, seed=4, salt="s", sites_path=path)["transformers"]
    placed = first.merge(sites, on="osm_node_id", suffixes=("", "_osm"))
    assert len(placed) == 3 and first["osm_node_id"].is_unique
    assert (placed["lat"] == placed["lat_osm"]).all() and (placed["lon"] == placed["lon_osm"]).all()
    assert first["osm_node_id"].tolist() == again["osm_node_id"].tolist()  # same seed, same sites


def test_more_transformers_than_sites_fails(tmp_path):
    _, path = _sites(tmp_path, 2)
    with pytest.raises(NotEnoughSitesError):
        simulate(transformers=3, days=1, seed=4, salt="s", sites_path=path)


def test_committed_snapshot_covers_make_sim():
    sites = load_sites()
    assert len(sites) >= 50 and sites["osm_node_id"].is_unique


def _buildings(tmp_path, sites, per_site: int):
    rows = [
        {
            "osm_node_id": site.osm_node_id,
            "osm_way_id": 1000 * site.osm_node_id + b,
            "lat": site.lat + b * 1e-5,
            "lon": site.lon,
            "distance_m": b * 1.1,
        }
        for site in sites.itertuples()
        for b in range(per_site)
    ]
    path = tmp_path / "buildings.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_each_clamped_home_has_exactly_one_clamp(tmp_path):
    sites, path = _sites(tmp_path, 3)
    tables = simulate(transformers=3, days=1, seed=4, salt="s", sites_path=path)
    homes, clamps = tables["sin_map"], tables["clamps"]
    clamped = set(homes.loc[homes["has_clamp"], "sin_hash"])
    assert set(clamps["sin_hash"]) == clamped and clamps["sin_hash"].is_unique
    assert clamps["clamp_id"].is_unique and clamps["clamp_id"].str.match(r"silip-node-\d{4}").all()
    assert (clamps["installed_at"] < clamps["last_seen_at"]).all()
    assert clamps["is_simulated"].all()


def test_homes_sit_on_nearby_buildings_and_share_when_there_are_too_few(tmp_path):
    sites, path = _sites(tmp_path, 3)
    buildings = _buildings(tmp_path, sites, per_site=5)
    tables = simulate(3, 1, 4, "s", sites_path=path, buildings_path=buildings)
    homes = tables["sin_map"].merge(
        tables["transformers"], on="transformer_id", suffixes=("", "_t")
    )
    assert homes["osm_way_id"].notna().all()  # every home got a building
    assert (homes["osm_way_id"] // 1000 == homes["osm_node_id"]).all()  # its own site's building
    assert homes.groupby("transformer_id")["osm_way_id"].nunique().eq(5).all()  # shared as units


def test_homes_scatter_near_the_transformer_without_buildings(tmp_path):
    _, path = _sites(tmp_path, 2)
    tables = simulate(2, 1, 4, "s", sites_path=path, buildings_path=tmp_path / "none.csv")
    homes = tables["sin_map"].merge(
        tables["transformers"], on="transformer_id", suffixes=("", "_t")
    )
    assert homes["osm_way_id"].isna().all()
    assert ((homes["lat"] - homes["lat_t"]).abs() < 0.002).all()  # within ~200 m
    assert ((homes["lon"] - homes["lon_t"]).abs() < 0.002).all()


def test_placing_homes_leaves_load_unchanged(tmp_path):
    sites, path = _sites(tmp_path, 2)
    buildings = _buildings(tmp_path, sites, per_site=5)
    with_buildings = simulate(2, 1, 4, "s", sites_path=path, buildings_path=buildings)
    without = simulate(2, 1, 4, "s", sites_path=path, buildings_path=tmp_path / "none.csv")
    pd.testing.assert_frame_equal(with_buildings["load"], without["load"])


def test_committed_building_snapshot_covers_every_site():
    from silip_ml.readings.osm_buildings import load_buildings

    buildings = load_buildings()
    assert set(load_sites()["osm_node_id"]) <= set(buildings["osm_node_id"])
