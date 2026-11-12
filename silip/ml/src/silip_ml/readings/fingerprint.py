"""Voltage fingerprinting: which transformer a home is really wired to.

When a transformer carries more load, current through its winding and lines drops the voltage at
every home it feeds. So a home's voltage dips together with the load of the transformer it is
really on. We score each candidate transformer by how strongly the home's voltage falls as that
transformer's load rises (negative correlation), and flag a mismatch with the records only when
the evidence is clear.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd

FISHER_MIN_SAMPLES = 3  # the Fisher z standard error is sqrt(1 / (n - 3)) per correlation


@dataclass(frozen=True)
class Fingerprint:
    """One home's verdict. `voltage_transformer` is None when the data cannot decide."""

    home: str
    record_transformer: str
    voltage_transformer: str | None
    confidence: float  # 0..1, how sure the best transformer beats the runner-up (see _confidence)
    mismatch: bool
    explanation: str


def _dip_score(voltage: pd.Series, load: pd.Series) -> float:
    """How often the voltage falls in the same step the load rises: -corr of the sample-to-sample
    changes, in -1..1 (nan if either never moves).

    Changes, not levels: a heat wave lifts every home at once, so levels correlate with every
    transformer. Each switch flick is its own piece of evidence in the changes.
    """
    dv, dl = voltage.diff().dropna().to_numpy(), load.diff().dropna().to_numpy()
    if dv.std() == 0 or dl.std() == 0:
        return float("nan")
    return float(-np.corrcoef(dv, dl)[0, 1])


def _confidence(best: float, runner_up: float, samples: int) -> float:
    """How sure we are that `best` beats `runner_up`, given `samples` changes: a one-sided Fisher z
    test on the two correlations. Approximate: it treats them as independent, though both use the
    same voltage series, so it can overstate certainty a little."""
    if samples <= FISHER_MIN_SAMPLES:
        return 0.0
    clip = 1 - 1e-6  # atanh(1) is infinite
    z = (
        np.arctanh(np.clip(best, -clip, clip)) - np.arctanh(np.clip(runner_up, -clip, clip))
    ) / math.sqrt(2 / (samples - FISHER_MIN_SAMPLES))
    return float(0.5 * (1 + math.erf(z / math.sqrt(2))))


def fingerprint(
    voltage: pd.DataFrame,
    load: pd.DataFrame,
    records: Mapping[str, str],
    *,
    min_load_swing: float,
    min_confidence: float,
    min_samples: int,
) -> list[Fingerprint]:
    """Match each home's voltage to the transformer load that best explains its dips.

    Args:
        voltage: one column per home, indexed by time (aligned samples, no gaps).
        load: one column per transformer total, same index as `voltage`.
        records: home -> transformer it is listed under.
        min_load_swing: a transformer whose load range is smaller than this cannot be judged.
        min_confidence: flag a mismatch only when the best transformer beats the runner-up with at
            least this confidence (see `_confidence`).
        min_samples: fewer aligned samples than this means "not enough data yet".
    """
    joined = voltage.join(load, how="inner").dropna()  # home and transformer names never clash
    swinging = [t for t in load.columns if np.ptp(joined[t].to_numpy()) >= min_load_swing]
    results = []
    for home, record in records.items():
        if len(joined) < min_samples or not swinging or home not in joined:
            results.append(
                Fingerprint(home, record, None, 0.0, False, "Not enough load change yet to decide.")
            )
            continue
        scores = {t: _dip_score(joined[home], joined[t]) for t in swinging}
        scores = {t: s for t, s in scores.items() if not np.isnan(s)}
        if not scores:
            results.append(
                Fingerprint(home, record, None, 0.0, False, "Voltage did not move; cannot decide.")
            )
            continue
        ranked = sorted(scores, key=scores.__getitem__, reverse=True)
        best = ranked[0]
        runner_up = scores[ranked[1]] if len(ranked) > 1 else 0.0
        confidence = _confidence(scores[best], runner_up, len(joined) - 1)
        mismatch = best != record and confidence >= min_confidence
        explanation = (
            f"Voltage dips with {best}, not {record}."
            if mismatch
            else f"Voltage dips with {best}, as recorded."
            if best == record
            else "Evidence is not clear enough to flag."
        )
        results.append(Fingerprint(home, record, best, confidence, mismatch, explanation))
    return results
