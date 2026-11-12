"""Compare any strategy with its baseline on simulated data, split by time.

    python -m silip_ml.backtest                          # every domain: baseline vs challenger
    python -m silip_ml.backtest --domain risk --strategy lightgbm

The last `HOLDOUT_DAYS` days are held out. Each held-out day is forecast and scored at 00:00
from the history before it. Trained strategies are the artifacts in `models/`; the backtest
refuses one whose training window reaches into the held-out days. Results are labeled Simulated.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from silip_ml.core.config import MlSettings, get_ml_settings
from silip_ml.core.registry import BASELINES, Task, create
from silip_ml.features import longest_run, to_grid
from silip_ml.load.metrics import mae_kw
from silip_ml.outages.metrics import eta_scores, locate_error_m
from silip_ml.readings.dataset import Dataset, load_dataset
from silip_ml.readings.domain import ASSUMED_POWER_FACTOR, STEPS_PER_DAY
from silip_ml.risk.domain import TRIP_LOAD_PCT, TRIP_MIN_STEPS
from silip_ml.risk.metrics import RiskCounts

HOLDOUT_DAYS = 7
DOMAINS: dict[str, Task] = {
    "load": "forecaster",
    "risk": "risk_scorer",
    "locate": "outage_locator",
    "eta": "eta_estimator",
}
# What `make backtest` compares with each baseline when no --strategy is given.
CHALLENGERS = {"load": "lightgbm", "risk": "lightgbm", "locate": "dbscan", "eta": "quantile_lgbm"}


class LeakageError(RuntimeError):
    """An exported model was trained on days the backtest holds out."""


@dataclass(frozen=True)
class Metric:
    name: str
    value: float
    n: int
    unit: str


def _holdout_days(load: pd.DataFrame) -> list[pd.Timestamp]:
    days = load["ts"].dt.normalize().drop_duplicates().sort_values()
    return list(days.iloc[-HOLDOUT_DAYS:])


def _check_trained_before(strategy: object, cutoff: pd.Timestamp) -> None:
    """Refuse an artifact whose training window reaches the held-out days."""
    artifact = getattr(strategy, "artifact", None)
    if artifact is None:
        return
    end = pd.Timestamp(artifact.metadata["training_window"]["end"])
    if end >= cutoff:
        raise LeakageError(f"model trained until {end}, but the holdout starts {cutoff}")


def _daily_forecasts(
    data: Dataset, forecaster_name: str
) -> list[tuple[pd.Timestamp, pd.DataFrame]]:
    days = _holdout_days(data.load)
    forecaster = create("forecaster", forecaster_name)
    _check_trained_before(forecaster, days[0])
    return [
        (day, forecaster.predict(data.load[data.load["ts"] < day], STEPS_PER_DAY)) for day in days
    ]


def backtest_load(data: Dataset, strategy: str, settings: MlSettings) -> list[Metric]:
    forecasts = pd.concat([f for _, f in _daily_forecasts(data, strategy)], ignore_index=True)
    mae, n = mae_kw(forecasts, data.load)
    return [Metric("Load MAE", mae, n, "kW")]


def _tripped(data: Dataset, day: pd.Timestamp) -> pd.Series:
    """Ground truth per transformer for `day`: the trip rule on true load when the data has it."""
    column = "true_kw" if "true_kw" in data.load.columns else "transformer_kw"
    actual = data.load[data.load["ts"].dt.normalize() == day]
    grid = to_grid(actual, column)
    rated = data.transformers.set_index("transformer_id").loc[grid.transformer_ids, "rated_kva"]
    pct = grid.values.T / (rated.to_numpy(dtype=np.float64)[:, None] * ASSUMED_POWER_FACTOR)
    runs = longest_run(pct > TRIP_LOAD_PCT)
    return pd.Series(runs >= TRIP_MIN_STEPS, index=grid.transformer_ids)


def risk_forecaster(strategy: str, settings: MlSettings) -> str:
    """The forecaster a risk scorer was trained on (from its metadata), else the configured one."""
    artifact = getattr(create("risk_scorer", strategy), "artifact", None)
    return str(artifact.metadata["forecaster"]) if artifact is not None else settings.forecaster


def backtest_risk(data: Dataset, strategy: str, settings: MlSettings) -> list[Metric]:
    days = _holdout_days(data.load)
    scorer = create("risk_scorer", strategy)
    _check_trained_before(scorer, days[0])
    counts = RiskCounts()
    for day, forecast in _daily_forecasts(data, settings.forecaster):
        tripped = _tripped(data, day)
        for output in scorer.score(forecast, data.transformers):
            counts = counts.add(
                output.tier == "Critical", bool(tripped.get(output.transformer_id, False))
            )
    return [
        Metric(
            "Risk recall, next 24 h scored at 00:00", counts.recall, counts.trips, "share of trips"
        ),
        Metric(
            "False alarms per transformer-month",
            counts.false_alarms_per_transformer_month,
            counts.windows,
            "count",
        ),
    ]


def _holdout_outages(data: Dataset) -> tuple[pd.DataFrame, pd.DataFrame]:
    cutoff = _holdout_days(data.load)[0]
    return data.outages[data.outages["start_ts"] < cutoff], data.outages[
        data.outages["start_ts"] >= cutoff
    ]


def backtest_locate(data: Dataset, strategy: str, settings: MlSettings) -> list[Metric]:
    _, test = _holdout_outages(data)
    pins = create("outage_locator", strategy).locate(
        data.signals[data.signals["outage_id"].isin(test["outage_id"])]
    )
    error, n = locate_error_m(pins, test)
    return [Metric("Outage locate error, median", error, n, "m")]


def backtest_eta(data: Dataset, strategy: str, settings: MlSettings) -> list[Metric]:
    train, test = _holdout_outages(data)
    estimates = create("eta_estimator", strategy).fit(train).predict(test)
    coverage, p50_error, n = eta_scores(estimates, test)
    return [
        Metric("ETA inside P10 to P90", coverage, n, "share"),
        Metric("ETA P50 absolute error", p50_error, n, "min"),
    ]


RUNNERS = {
    "load": backtest_load,
    "risk": backtest_risk,
    "locate": backtest_locate,
    "eta": backtest_eta,
}


def run(domain: str, strategy: str, data: Dataset, settings: MlSettings) -> list[str]:
    """Markdown rows comparing `strategy` with the domain's baseline."""
    baseline = BASELINES[DOMAINS[domain]]
    if domain == "risk":  # both scorers read the same forecasts: the challenger's forecaster
        settings = settings.model_copy(update={"forecaster": risk_forecaster(strategy, settings)})
    base = RUNNERS[domain](data, baseline, settings)
    other = base if strategy == baseline else RUNNERS[domain](data, strategy, settings)
    return [
        f"| {domain} | {b.name} ({b.unit}) | {baseline} | {b.value:.3g} | {strategy} | {o.value:.3g} | {b.n} |"
        for b, o in zip(base, other, strict=True)
    ]


def main() -> None:
    settings = get_ml_settings()
    parser = argparse.ArgumentParser(description="Backtest strategies against their baselines.")
    parser.add_argument("--domain", choices=[*DOMAINS, "all"], default="all")
    parser.add_argument("--strategy", help="strategy name (default: the configured one)")
    parser.add_argument("--data-dir", type=Path, default=settings.data_dir)
    parser.add_argument("--report", type=Path, default=Path("reports/backtest.md"))
    args = parser.parse_args()

    data = load_dataset(args.data_dir)
    domains = list(DOMAINS) if args.domain == "all" else [args.domain]
    rows = []
    for domain in domains:
        strategy = args.strategy or CHALLENGERS[domain]
        rows += run(domain, strategy, data, settings)

    report = "\n".join(
        [
            "# Backtest (Simulated data)",
            "",
            f"Data: `{args.data_dir}`, held-out last {HOLDOUT_DAYS} days. Every number is from simulated data.",
            f"Risk forecasts come from `{risk_forecaster(CHALLENGERS['risk'], settings)}` for both scorers.",
            "",
            "| Domain | Metric | Baseline | Value | Strategy | Value | n |",
            "|---|---|---|---|---|---|---|",
            *rows,
            "",
        ]
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
