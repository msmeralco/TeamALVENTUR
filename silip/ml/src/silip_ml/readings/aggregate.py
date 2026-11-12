"""Sum household readings by SIN into transformer load (docs/SPEC.md#data: resample, sum)."""

from __future__ import annotations

import pandas as pd

from silip_ml.readings.domain import INTERVAL


def sum_by_transformer(readings: pd.DataFrame, interval: str = INTERVAL) -> pd.DataFrame:
    """Resample each home to `interval` (mean kW), then sum homes per transformer.

    Args:
        readings: columns `sin_hash, transformer_id, ts, power_kw`.

    Returns:
        Columns `transformer_id, ts, measured_kw, homes_reporting`.
    """
    binned = readings.assign(ts=readings["ts"].dt.floor(interval))
    per_home = binned.groupby(["transformer_id", "sin_hash", "ts"], as_index=False).agg(
        power_kw=("power_kw", "mean")
    )
    return per_home.groupby(["transformer_id", "ts"], as_index=False).agg(
        measured_kw=("power_kw", "sum"), homes_reporting=("sin_hash", "nunique")
    )
