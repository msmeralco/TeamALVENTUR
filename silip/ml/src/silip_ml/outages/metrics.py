"""Outage metrics for the backtest."""

from __future__ import annotations

import pandas as pd

from silip_ml.outages.domain import haversine_m


def locate_error_m(pins: pd.DataFrame, truth: pd.DataFrame) -> tuple[float, int]:
    """Median distance (m) from each pin to the true location, and how many outages matched."""
    joined = pins.merge(truth[["outage_id", "lat", "lon"]], on="outage_id", suffixes=("", "_true"))
    errors = haversine_m(joined["lat"], joined["lon"], joined["lat_true"], joined["lon_true"])
    return float(pd.Series(errors).median()), len(joined)


def eta_scores(estimates: pd.DataFrame, truth: pd.DataFrame) -> tuple[float, float, int]:
    """Share of outages restored inside P10 to P90, P50 absolute error (min), and count."""
    joined = estimates.merge(truth[["outage_id", "duration_min"]], on="outage_id")
    actual = joined["duration_min"]
    inside = actual.between(joined["eta_p10_min"], joined["eta_p90_min"])
    return float(inside.mean()), float((joined["eta_p50_min"] - actual).abs().mean()), len(joined)
