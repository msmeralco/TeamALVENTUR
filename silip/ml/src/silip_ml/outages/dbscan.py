"""DBSCAN on last gasps and reports; the pin is the centroid of the largest cluster."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

from silip_ml.core.registry import register
from silip_ml.outages.domain import EARTH_RADIUS_M


@register("outage_locator", "dbscan")
class DBSCANLocator:
    """Dense clusters of pings beat a single early report."""

    def __init__(self, eps_m: float = 100.0, min_samples: int = 3) -> None:
        self._eps_rad = eps_m / EARTH_RADIUS_M
        self._min_samples = min_samples

    def _pin(self, points: pd.DataFrame) -> tuple[float, float]:
        coords = np.radians(points[["lat", "lon"]].to_numpy())
        labels = DBSCAN(
            eps=self._eps_rad, min_samples=self._min_samples, metric="haversine"
        ).fit_predict(coords)
        clustered = labels[labels >= 0]
        if clustered.size == 0:  # no dense cluster: fall back to the median of all points
            return float(points["lat"].median()), float(points["lon"].median())
        largest = points[labels == np.bincount(clustered).argmax()]
        return float(largest["lat"].mean()), float(largest["lon"].mean())

    def locate(self, signals: pd.DataFrame) -> pd.DataFrame:
        rows = [
            {"outage_id": outage_id, **dict(zip(("lat", "lon"), self._pin(points), strict=True))}
            for outage_id, points in signals.groupby("outage_id")
        ]
        return pd.DataFrame(rows, columns=["outage_id", "lat", "lon"])
