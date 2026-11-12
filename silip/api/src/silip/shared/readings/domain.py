"""The DataSource port. Every strategy returns the same columns, so services never know which.

transformers: transformer_id, rated_kva, homes, coverage_pct, lat, lon, is_simulated
load:         transformer_id, ts, transformer_kw, is_simulated
outages:      outage_id, transformer_id, start_ts, cause, duration_min (null while open), lat, lon,
              is_simulated
signals:      outage_id, kind (last_gasp | report), ts, lat, lon
clamps:       clamp_id, transformer_id, lat, lon, ct_model, installed_at, last_seen_at (null if
              never seen), is_simulated; one row per installed clamp, never a sin_hash
clamp counts: transformer_id, clamps_installed, clamps_online, is_simulated; counts only
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

import pandas as pd

# Four missed 15-minute readings. Design choice, no source: [VERIFY] against field reconnect data.
OFFLINE_AFTER = pd.Timedelta(minutes=60)
CLAMP_COUNT_COLUMNS = ["transformer_id", "clamps_installed", "clamps_online", "is_simulated"]


class DataSource(Protocol):
    """Reads SILIP tables from one backend (simulated CSVs, clamp readings, smart meters)."""

    def transformers(self) -> pd.DataFrame: ...

    def load(self, since: datetime | None = None) -> pd.DataFrame:
        """Load rows with `ts > since` (all rows when None)."""
        ...

    def latest_load_ts(self) -> pd.Timestamp | None:
        """The latest 15-minute load interval, by the data's own clock (never now()); None if empty."""
        ...

    def outages(self) -> pd.DataFrame: ...

    def outage_signals(self) -> pd.DataFrame: ...

    def clamps(self) -> pd.DataFrame: ...

    def clamp_counts(self, as_of: datetime) -> pd.DataFrame:
        """Per transformer with clamps: installed, and online (seen within OFFLINE_AFTER of
        `as_of`). Aggregated where the data lives; never a clamp_id, sin_hash or home location."""
        ...
