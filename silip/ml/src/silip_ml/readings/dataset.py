"""Load the simulated CSVs written by `notebooks/00_generate_mock_data.ipynb`."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

FILES = {
    "transformers": "transformers.csv",
    "load": "transformer_load_15m.csv",
    "outages": "outages.csv",
    "signals": "outage_signals.csv",
    "households": "household_load_15m.csv",
}
# Weather tables are optional, so sims made before them still load (as empty frames).
OPTIONAL_FILES = {"weather": "weather_forecast_hourly.csv", "conditions": "weather_15m.csv"}
_TIME_COLUMNS = {
    "load": ["ts"],
    "outages": ["start_ts"],
    "signals": ["ts"],
    "households": ["ts"],
    "weather": ["issued_at", "ts"],
    "conditions": ["ts"],
}


@dataclass(frozen=True)
class Dataset:
    """All tables of one simulated run. Every row has `is_simulated`."""

    transformers: pd.DataFrame
    load: pd.DataFrame
    outages: pd.DataFrame
    signals: pd.DataFrame
    households: pd.DataFrame
    # Hourly archive and day-ahead forecasts (`issued_at, ts, cell_id, ..., kind`). Read only rows
    # issued at or before the scoring time.
    weather: pd.DataFrame = field(default_factory=pd.DataFrame)
    # The simulator's true weather per 15 minutes (`weather` = clear|hot_spell|rain|typhoon); for
    # grouping backtest days only, never a model input.
    conditions: pd.DataFrame = field(default_factory=pd.DataFrame)


def load_dataset(data_dir: Path) -> Dataset:
    """Read every table from `data_dir`.

    Raises:
        FileNotFoundError: if a file is missing (run `make sim` first).
    """
    tables: dict[str, pd.DataFrame] = {}
    for name, filename in (FILES | OPTIONAL_FILES).items():
        path = Path(data_dir) / filename
        if not path.exists():
            if name in OPTIONAL_FILES:
                continue
            raise FileNotFoundError(f"{path} not found; run `make sim` first")
        frame = pd.read_csv(path)
        for column in _TIME_COLUMNS.get(name, []):
            frame[column] = pd.to_datetime(frame[column])
        tables[name] = frame
    return Dataset(**tables)
