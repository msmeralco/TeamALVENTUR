"""Turn the last few minutes of bench readings into what the /demo page shows."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from silip.bench.domain import (
    BenchFingerprint,
    BenchHomeState,
    BenchSnapshot,
    BenchTransformerState,
    NotBenchError,
)
from silip.shared.bench import config
from silip.shared.bench.domain import W_PER_KW, BenchReadings, samples, step_up, tier_now
from silip_ml.readings.fingerprint import fingerprint

LIVE_WINDOW = timedelta(seconds=30)  # the mode label follows the latest readings, not old ones


def _ev_reason(power_w: pd.Series, label: str) -> str | None:
    if step_up(power_w.dropna().to_numpy(), config.EV_STEP_W, config.EV_HOLD_SAMPLES) is None:
        return None
    return f"{label} added a large new load (likely EV)"


def _home_state(label: str, rows: pd.DataFrame) -> BenchHomeState:
    if rows.empty:
        return BenchHomeState(label=label, watts=None, volts=None, powered=True, updated_at=None)
    last = rows.iloc[-1]
    powered = pd.isna(last["event"])
    return BenchHomeState(
        label=label,
        watts=float(last["power_kw"]) * W_PER_KW if powered else 0.0,
        volts=float(last["voltage_v"]) if powered else 0.0,
        powered=powered,
        updated_at=pd.Timestamp(last["ts"]).to_pydatetime(),
    )


def _fingerprints(
    volts: pd.DataFrame, power_w: pd.DataFrame, now: datetime
) -> list[BenchFingerprint]:
    if volts.empty:
        return []
    since = pd.Timestamp(now - timedelta(seconds=config.FINGERPRINT_WINDOW_S))
    by_label = {home.sin_hash: home.label for home in config.HOMES}
    window_v = volts[volts.index > since].rename(columns=by_label)
    window_p = power_w[power_w.index > since].rename(columns=by_label)
    records = {h.label: h.record_transformer for h in config.HOMES if h.label in window_v}
    load = pd.DataFrame(
        {
            t.transformer_id: window_p[
                [h for h, r in records.items() if r == t.transformer_id]
            ].sum(axis=1)
            for t in config.TRANSFORMERS
        }
    )
    found = fingerprint(
        window_v[list(records)],
        load,
        records,
        min_load_swing=config.FINGERPRINT_MIN_LOAD_SWING_W,
        min_confidence=config.FINGERPRINT_MIN_CONFIDENCE,
        min_samples=config.FINGERPRINT_MIN_SAMPLES,
    )
    return [BenchFingerprint(**vars(f)) for f in found]


def snapshot(readings: pd.DataFrame, now: datetime) -> BenchSnapshot:
    """Both bench transformers: each home's latest watts and volts, the total summed by SIN, the
    live tier with reasons, and the voltage fingerprint of every home."""
    known = config.home_by_hash()
    readings = readings[readings["sin_hash"].isin(list(known))].sort_values("ts")
    power_w = samples(readings, "power_kw") * W_PER_KW
    volts = samples(readings, "voltage_v")
    transformers = []
    for t in config.TRANSFORMERS:
        on_record = [h for h in config.HOMES if h.record_transformer == t.transformer_id]
        homes = [
            _home_state(h.label, readings[readings["sin_hash"] == h.sin_hash]) for h in on_record
        ]
        reporting = [s for s in homes if s.watts is not None]
        total_w = sum(s.watts or 0.0 for s in reporting)
        columns = [h.sin_hash for h in on_record if h.sin_hash in power_w]
        history = power_w[columns].sum(axis=1) / t.rated_w if columns else pd.Series(dtype=float)
        powered = not reporting or any(s.powered for s in reporting)
        tier, over = tier_now(history) if powered else ("OK", 0)
        reasons = (
            [f"Load {total_w / t.rated_w:.0%} of rating now"]
            if powered
            else ["No power: homes sent a last gasp"]
        )
        if over:
            reasons.append(f"Above 100% of rating for {over * config.SAMPLE_INTERVAL_S:.0f} s")
        reasons += [
            r
            for h in on_record
            if h.sin_hash in power_w and (r := _ev_reason(power_w[h.sin_hash], h.label))
        ]
        transformers.append(
            BenchTransformerState(
                transformer_id=t.transformer_id,
                rated_w=t.rated_w,
                total_w=round(total_w, 3),
                load_pct=total_w / t.rated_w,
                tier=tier,
                reasons=reasons,
                homes_reporting=len(reporting),
                homes_on_record=len(on_record),
                homes=homes,
                powered=powered,
            )
        )
    recent = readings[pd.to_datetime(readings["ts"], utc=True) > pd.Timestamp(now - LIVE_WINDOW)]
    simulated = bool(recent["is_simulated"].any()) if not recent.empty else False
    return BenchSnapshot(
        as_of=now,
        mode=None if recent.empty else ("replay" if simulated else "live"),
        is_simulated=simulated,
        sample_interval_s=config.SAMPLE_INTERVAL_S,
        transformers=transformers,
        fingerprints=_fingerprints(volts, power_w, now),
    )


def bench_snapshot(
    source: BenchReadings, now: datetime, transformer_id: str | None = None
) -> BenchSnapshot:
    """The snapshot for the whole rig, or for one bench transformer.

    Raises:
        NotBenchError: `transformer_id` is not a bench transformer.
    """
    ids = {t.transformer_id for t in config.TRANSFORMERS}
    if transformer_id is not None and (
        not config.is_bench(transformer_id) or transformer_id not in ids
    ):
        raise NotBenchError(transformer_id)
    result = snapshot(source.recent(now - timedelta(seconds=config.WINDOW_S)), now)
    if transformer_id is None:
        return result
    return result.model_copy(
        update={
            "transformers": [t for t in result.transformers if t.transformer_id == transformer_id]
        }
    )
