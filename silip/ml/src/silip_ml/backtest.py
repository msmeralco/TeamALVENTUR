"""Compare any strategy with its baseline on simulated data, split by time.

    python -m silip_ml.backtest                          # every domain, configured strategies
    python -m silip_ml.backtest --domain risk --strategy lightgbm

The last `HOLDOUT_DAYS` days are held out. Each held-out day is forecast and scored at 00:00
from the history before it. Results are labeled Simulated.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from silip_ml.core.config import MlSettings, get_ml_settings
from silip_ml.core.registry import BASELINES, Task, create
from silip_ml.load.metrics import mae_kw
from silip_ml.outages.metrics import eta_scores, locate_error_m
from silip_ml.readings.dataset import Dataset, load_dataset
from silip_ml.readings.domain import STEPS_PER_DAY, load_pct
from silip_ml.risk.domain import is_trip
from silip_ml.risk.metrics import RiskCounts

HOLDOUT_DAYS = 7
DOMAINS: dict[str, Task] = {
    "load": "forecaster",
    "risk": "risk_scorer",
    "locate": "outage_locator",
    "eta": "eta_estimator",
}


@dataclass(frozen=True)
class Metric:
    name: str
    value: float
    n: int
    unit: str


def _holdout_days(load: pd.DataFrame) -> list[pd.Timestamp]:
    days = load["ts"].dt.normalize().drop_duplicates().sort_values()
    return list(days.iloc[-HOLDOUT_DAYS:])


def _daily_forecasts(
    data: Dataset, forecaster_name: str
) -> list[tuple[pd.Timestamp, pd.DataFrame]]:
    cutoff = _holdout_days(data.load)[0]
    forecaster = create("forecaster", forecaster_name).fit(data.load[data.load["ts"] < cutoff])
    return [
        (day, forecaster.predict(data.load[data.load["ts"] < day], STEPS_PER_DAY))
        for day in _holdout_days(data.load)
    ]


def backtest_load(data: Dataset, strategy: str, settings: MlSettings) -> list[Metric]:
    forecasts = pd.concat([f for _, f in _daily_forecasts(data, strategy)], ignore_index=True)
    mae, n = mae_kw(forecasts, data.load)
    return [Metric("Load MAE", mae, n, "kW")]


def backtest_risk(data: Dataset, strategy: str, settings: MlSettings) -> list[Metric]:
    days = _holdout_days(data.load)
    scorer = create("risk_scorer", strategy).fit(
        data.load[data.load["ts"] < days[0]], data.transformers
    )
    rated = data.transformers.set_index("transformer_id")["rated_kva"]
    counts = RiskCounts()
    for day, forecast in _daily_forecasts(data, settings.forecaster):
        actual = data.load[data.load["ts"].dt.normalize() == day]
        for output in scorer.score(forecast, data.transformers):
            kw = actual.loc[actual["transformer_id"] == output.transformer_id].sort_values("ts")[
                "transformer_kw"
            ]
            tripped = is_trip(load_pct(kw.to_numpy(), rated[output.transformer_id]))
            counts = counts.add(output.tier == "Critical", tripped)
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
        strategy = args.strategy or getattr(settings, DOMAINS[domain])
        rows += run(domain, strategy, data, settings)

    report = "\n".join(
        [
            "# Backtest (Simulated data)",
            "",
            f"Data: `{args.data_dir}`, held-out last {HOLDOUT_DAYS} days. Every number is from simulated data.",
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
