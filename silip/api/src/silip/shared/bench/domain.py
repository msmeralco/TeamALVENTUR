"""Bench rig reads and the pure rules behind the live demo: status, EV step, last-gasp outage.

readings: sin_hash, transformer_id (as recorded), ts, voltage_v, power_kw, event, is_simulated
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

import numpy as np
import pandas as pd

from silip.shared.bench import config
from silip_ml.risk.domain import CRITICAL_LOAD_PCT, WATCH_LOAD_PCT

Tier = Literal["OK", "Watch", "Critical"]
W_PER_KW = 1000


class BenchReadings(Protocol):
    """Recent readings from bench transformers only (`BENCH-*`)."""

    def recent(self, since: datetime) -> pd.DataFrame: ...


def samples(readings: pd.DataFrame, column: str) -> pd.DataFrame:
    """One column per home (sin_hash), one row per sample interval, gaps carried forward."""
    if readings.empty:
        return pd.DataFrame()
    normal = readings[readings["event"].isna()]
    bucket = pd.to_datetime(normal["ts"], utc=True).dt.floor(f"{config.SAMPLE_INTERVAL_S}s")
    table = normal.assign(bucket=bucket).pivot_table(
        index="bucket", columns="sin_hash", values=column, aggfunc="last"
    )
    full = pd.date_range(table.index.min(), table.index.max(), freq=f"{config.SAMPLE_INTERVAL_S}s")
    return table.reindex(full).ffill()


def tier_now(load_pct: pd.Series) -> tuple[Tier, int]:
    """Tier from the last HOLD_SAMPLES samples, and how many samples in a row are over 100%.

    Same meaning as the baseline rule ("over 100% of rating, held"), with time compressed.
    """
    recent = load_pct.dropna().to_numpy()
    over = 0
    for value in recent[::-1]:
        if value <= CRITICAL_LOAD_PCT:
            break
        over += 1
    held = recent[-config.HOLD_SAMPLES :]
    if over >= config.HOLD_SAMPLES:
        return "Critical", over
    if len(held) == config.HOLD_SAMPLES and (held >= WATCH_LOAD_PCT).all():
        return "Watch", over
    return "OK", over


def step_up(power_w: np.ndarray, step_w: float, hold: int) -> int | None:
    """Index where power rose by at least `step_w` and stayed up for `hold` samples; else None.

    A short spike falls back before `hold` samples. A slow ramp never jumps `step_w` between
    the `hold` samples before and after any point.
    """
    for i in range(hold, len(power_w) - hold + 1):
        before = power_w[i - hold : i].mean()
        after = power_w[i : i + hold]
        if (after - before >= step_w).all() and (power_w[i:] - before >= step_w).all():
            return i
    return None


@dataclass(frozen=True)
class BenchOutage:
    outage_id: str
    transformer_id: str
    started_at: datetime
    restored_at: datetime | None
    homes: int  # homes that sent a last gasp
    is_simulated: bool


def gasp_outages(readings: pd.DataFrame) -> list[BenchOutage]:
    """Open an outage when LAST_GASP_MIN_HOMES homes on one transformer gasp within the window.

    Restored when any of those homes sends a normal reading again. Derived on every read, so no
    row is ever updated (the app role cannot UPDATE).
    """
    if readings.empty:
        return []
    window = pd.Timedelta(seconds=config.LAST_GASP_WINDOW_S)
    outages = []
    ts = pd.to_datetime(readings["ts"], utc=True)
    gasps = readings[readings["event"] == "last_gasp"].assign(ts=ts)
    normal = readings[readings["event"].isna()].assign(ts=ts)
    for transformer_id, group in gasps.sort_values("ts").groupby("transformer_id"):
        start = None
        for _, first in group.iterrows():
            if start is not None and first["ts"] <= start:
                continue  # already part of an outage we recorded
            burst = group[(group["ts"] >= first["ts"]) & (group["ts"] <= first["ts"] + window)]
            homes = set(burst["sin_hash"])
            if len(homes) < config.LAST_GASP_MIN_HOMES:
                continue
            began = first["ts"]
            back = normal[normal["sin_hash"].isin(homes) & (normal["ts"] > burst["ts"].max())]
            restored = back["ts"].min() if not back.empty else None
            outages.append(
                BenchOutage(
                    outage_id=f"{transformer_id}-{int(began.timestamp())}",
                    transformer_id=str(transformer_id),
                    started_at=began.to_pydatetime(),
                    restored_at=None if restored is None else restored.to_pydatetime(),
                    homes=len(homes),
                    is_simulated=bool(burst["is_simulated"].any()),
                )
            )
            start = restored if restored is not None else pd.Timestamp.max.tz_localize("UTC")
    return outages
