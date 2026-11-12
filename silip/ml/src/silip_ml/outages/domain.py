"""Ports for locating outages and estimating restoration, plus distance math.

Signals columns: outage_id, kind (last_gasp | report), ts, lat, lon.
Outages columns: outage_id, start_ts, cause (plus duration_min when known).
"""

from __future__ import annotations

from typing import Protocol, Self

import numpy as np
import numpy.typing as npt
import pandas as pd

EARTH_RADIUS_M = 6_371_000


class OutageLocator(Protocol):
    """Places one pin per outage from last-gasp pings and customer reports."""

    def locate(self, signals: pd.DataFrame) -> pd.DataFrame:
        """Return columns `outage_id, lat, lon`."""
        ...


class EtaEstimator(Protocol):
    """Estimates restoration time as a P10 to P90 range in minutes."""

    def fit(self, outages: pd.DataFrame) -> Self: ...

    def predict(self, outages: pd.DataFrame) -> pd.DataFrame:
        """Return columns `outage_id, eta_p10_min, eta_p50_min, eta_p90_min`."""
        ...


def haversine_m(
    lat1: npt.ArrayLike, lon1: npt.ArrayLike, lat2: npt.ArrayLike, lon2: npt.ArrayLike
) -> np.ndarray:
    """Great-circle distance in metres."""
    lat1, lon1, lat2, lon2 = (
        np.radians(np.asarray(v, dtype=float)) for v in (lat1, lon1, lat2, lon2)
    )
    a = (
        np.sin((lat2 - lat1) / 2) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(a))
