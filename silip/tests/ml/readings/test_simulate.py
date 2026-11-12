import subprocess
import sys

import pandas as pd


def test_simulator_outputs_labeled_and_hashed(tmp_path):
    out = tmp_path / "sim"
    subprocess.run([sys.executable, "sim/simulate.py", "--transformers", "3", "--days", "2", "--out", str(out)], check=True)
    sins = pd.read_csv(out / "sin_map.csv")
    load = pd.read_csv(out / "transformer_load_15m.csv")
    assert sins["is_simulated"].all() and load["is_simulated"].all()
    assert sins["sin_hash"].str.len().eq(64).all()  # SHA-256 hex, never raw SINs
    assert len(load) == 3 * 2 * 96
