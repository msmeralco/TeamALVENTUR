"""Shared fixtures: the small simulated dataset that notebooks/00_generate_mock_data.ipynb writes.

Regenerate with `SIM_SCALE=test` (see notebooks/README.md). Every row is simulated; SINs are hashes.
"""

from pathlib import Path

import pytest

from silip_ml.readings.dataset import Dataset, load_dataset

FIXTURE_SIM = Path(__file__).parent / "fixtures" / "sim"


@pytest.fixture(scope="session")
def sim_dir() -> Path:
    return FIXTURE_SIM


@pytest.fixture(scope="session")
def dataset(sim_dir: Path) -> Dataset:
    return load_dataset(sim_dir)
