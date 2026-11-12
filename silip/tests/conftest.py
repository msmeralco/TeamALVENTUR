"""Shared fixtures: one small simulated dataset per test session."""

from pathlib import Path

import pytest

from silip_ml.readings.dataset import Dataset, load_dataset
from silip_ml.readings.simulate import simulate, write

TEST_SALT = "test-salt"


@pytest.fixture(scope="session")
def sim_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("sim")
    write(simulate(transformers=6, days=16, seed=3, salt=TEST_SALT), out)
    return out


@pytest.fixture(scope="session")
def dataset(sim_dir: Path) -> Dataset:
    return load_dataset(sim_dir)
