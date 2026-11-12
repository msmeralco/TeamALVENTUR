import pandas as pd
import pytest

from silip.shared.load_sim import TABLES, NotSimulatedError, read_table


def test_every_table_reads_its_columns_and_keeps_is_simulated(sim_dir):
    for table in TABLES:
        frame = read_table(sim_dir, table)
        assert list(frame.columns) == list(table.columns), table.name
        assert not frame.empty, table.name
        assert all(type(value) is bool for value in frame["is_simulated"]), table.name
        assert frame["is_simulated"].all(), table.name  # the simulator never writes False


def test_open_outages_have_null_duration(sim_dir):
    outages = read_table(sim_dir, next(t for t in TABLES if t.name == "outage"))
    assert all(value is None or isinstance(value, int) for value in outages["duration_min"])


def test_a_sin_that_is_not_a_hash_is_refused(sim_dir, tmp_path):
    sin_map = pd.read_csv(sim_dir / "sin_map.csv")
    sin_map.loc[0, "sin_hash"] = "1234567890"
    sin_map.to_csv(tmp_path / "sin_map.csv", index=False)
    household = next(t for t in TABLES if t.name == "household")
    with pytest.raises(ValueError, match="sin_hash"):
        read_table(tmp_path, household)


def test_a_row_that_is_not_simulated_is_refused(sim_dir, tmp_path):
    outages = pd.read_csv(sim_dir / "outages.csv")
    outages.loc[0, "is_simulated"] = False
    outages.to_csv(tmp_path / "outages.csv", index=False)
    outage = next(t for t in TABLES if t.name == "outage")
    with pytest.raises(NotSimulatedError, match="outages.csv"):
        read_table(tmp_path, outage)
