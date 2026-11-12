"""The DataSource port. Every strategy returns the same columns, so services never know which.

transformers: transformer_id, rated_kva, homes, coverage_pct, lat, lon, is_simulated
load:         transformer_id, ts, transformer_kw, is_simulated
outages:      outage_id, transformer_id, start_ts, cause, duration_min (null while open), lat, lon,
              is_simulated
signals:      outage_id, kind (last_gasp | report), ts, lat, lon
usage:        ts, power_kw, is_simulated
"""

from __future__ import annotations

from typing import Protocol

import pandas as pd


class DataSource(Protocol):
    """Reads SILIP tables from one backend (simulated CSVs, clamp readings, smart meters)."""

    def transformers(self) -> pd.DataFrame: ...

    def load(self) -> pd.DataFrame: ...

    def outages(self) -> pd.DataFrame: ...

    def outage_signals(self) -> pd.DataFrame: ...

    def household_usage(self, sin_hash: str) -> pd.DataFrame: ...

    def sin_hash_for_account(self, subject: str) -> str | None:
        """The household linked to a Cognito user (`sub`), or None if none is linked."""
        ...
