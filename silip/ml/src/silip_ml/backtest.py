"""Compare strategies with their baseline on simulated data, split by time.

    python -m silip_ml.backtest                          # every domain: baseline vs challengers
    python -m silip_ml.backtest --domain risk --strategy lightgbm

The last `HOLDOUT_DAYS` days are held out. Each held-out day is forecast and scored at 00:00
from the history before it, with weather rows issued by then. Trained strategies are the artifacts
in `models/`; the backtest refuses one whose training window reaches into the held-out days.
Results are labeled Simulated.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from silip_ml.core.config import MlSettings, get_ml_settings
from silip_ml.core.registry import BASELINES, Task, create
from silip_ml.ev import exposure, normalise_stations
from silip_ml.features import WeatherInput, issue_cutoff, longest_run, to_grid, weather_input
from silip_ml.load.metrics import mae_kw
from silip_ml.outages.metrics import eta_scores, locate_error_m
from silip_ml.readings.dataset import Dataset, load_dataset
from silip_ml.readings.domain import ASSUMED_POWER_FACTOR, STEPS_PER_DAY
from silip_ml.risk.domain import TRIP_LOAD_PCT, TRIP_MIN_STEPS
from silip_ml.risk.metrics import RiskCounts

HOLDOUT_DAYS = 7
EARLY_LEAD = pd.Timedelta(hours=12)  # SPEC target: flagged at least 12 h before the trip
DOMAINS: dict[str, Task] = {
    "load": "forecaster",
    "risk": "risk_scorer",
    "locate": "outage_locator",
    "eta": "eta_estimator",
}
# What `make backtest` compares with each baseline when no --strategy is given: the current
# challenger first, then any new one.
CHALLENGERS: dict[str, list[str]] = {
    "load": ["lightgbm", "lightgbm_weather"],
    "risk": ["lightgbm", "lightgbm_weather_ev"],
    "locate": ["dbscan"],
    "eta": ["quantile_lgbm"],
}
STATIONS_FILE = Path("data/evcs_locations.csv")  # DOE list, delivered by another session


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


def weather_known_at(data: Dataset, as_of: pd.Timestamp) -> WeatherInput | None:
    """Weather rows issued by 00:00 (Manila) of `as_of`'s day, the only ones a run then could read."""
    if data.weather.empty:
        return None
    issued = pd.to_datetime(data.weather["issued_at"], utc=True)
    rows = data.weather[(issued <= issue_cutoff(as_of)).to_numpy()]
    return weather_input(rows, data.transformers)


def _daily_forecasts(
    data: Dataset, forecaster_name: str
) -> list[tuple[pd.Timestamp, pd.DataFrame]]:
    days = _holdout_days(data.load)
    forecaster = create("forecaster", forecaster_name)
    _check_trained_before(forecaster, days[0])
    return [
        (
            day,
            forecaster.predict(
                data.load[data.load["ts"] < day], STEPS_PER_DAY, weather_known_at(data, day)
            ),
        )
        for day in days
    ]


def backtest_load(data: Dataset, strategy: str, settings: MlSettings) -> list[Metric]:
    forecasts = pd.concat([f for _, f in _daily_forecasts(data, strategy)], ignore_index=True)
    mae, n = mae_kw(forecasts, data.load)
    metrics = [Metric("Load MAE", mae, n, "kW")]
    rated = data.transformers.set_index("transformer_id")["rated_kva"]
    for kva in sorted(rated.unique()):
        ids = rated.index[rated == kva]
        mae, n = mae_kw(forecasts[forecasts["transformer_id"].isin(ids)], data.load)
        metrics.append(Metric(f"Load MAE, {kva:g} kVA", mae, n, "kW"))
    if not data.conditions.empty:
        hot = data.conditions.loc[data.conditions["weather"] == "hot_spell", "ts"]
        mae, n = mae_kw(
            forecasts[forecasts["ts"].dt.normalize().isin(hot.dt.normalize())], data.load
        )
        metrics.append(Metric("Load MAE, hot-spell days", mae, n, "kW"))
    return metrics


def _tripped(data: Dataset, day: pd.Timestamp) -> pd.DataFrame:
    """Per transformer for `day`: did it trip (rule on true load when the data has it), and was
    the trip completed at least `EARLY_LEAD` after the 00:00 score."""
    column = "true_kw" if "true_kw" in data.load.columns else "transformer_kw"
    actual = data.load[data.load["ts"].dt.normalize() == day]
    grid = to_grid(actual, column)
    rated = data.transformers.set_index("transformer_id").loc[grid.transformer_ids, "rated_kva"]
    over = grid.values.T / (rated.to_numpy(dtype=np.float64)[:, None] * ASSUMED_POWER_FACTOR)
    over = over > TRIP_LOAD_PCT
    tripped = longest_run(over) >= TRIP_MIN_STEPS
    run = np.zeros(over.shape[0], dtype=np.int64)
    trip_step = np.full(over.shape[0], -1)
    for step, column_over in enumerate(over.T):  # first step where a run reaches the minimum
        run = (run + 1) * column_over
        trip_step = np.where((trip_step < 0) & (run == TRIP_MIN_STEPS), step, trip_step)
    trip_ts = grid.ts(np.maximum(trip_step, 0))
    early = tripped & np.asarray(trip_ts - day >= EARLY_LEAD)
    return pd.DataFrame({"tripped": tripped, "early": early}, index=grid.transformer_ids)


def risk_forecaster(strategy: str, settings: MlSettings) -> str:
    """The forecaster a risk scorer was trained on (from its metadata), else the configured one."""
    artifact = getattr(create("risk_scorer", strategy), "artifact", None)
    return str(artifact.metadata["forecaster"]) if artifact is not None else settings.forecaster


def _transformers_with_stations(data: Dataset) -> pd.DataFrame:
    """Transformers plus `ev_stations_within` from the DOE list, when it has landed."""
    if not STATIONS_FILE.exists():
        return data.transformers
    stations, _, _ = normalise_stations(pd.read_csv(STATIONS_FILE))
    near = exposure(data.transformers, stations).set_index("transformer_id")["stations_within"]
    return data.transformers.assign(
        ev_stations_within=data.transformers["transformer_id"].map(near).to_numpy()
    )


def backtest_risk(data: Dataset, strategy: str, settings: MlSettings) -> list[Metric]:
    days = _holdout_days(data.load)
    scorer = create("risk_scorer", strategy)
    _check_trained_before(scorer, days[0])
    transformers = _transformers_with_stations(data)
    counts = RiskCounts()
    for day, forecast in _daily_forecasts(data, settings.forecaster):
        truth = _tripped(data, day)
        outputs = scorer.score(
            forecast, transformers, weather_known_at(data, day), data.load[data.load["ts"] < day]
        )
        for output in outputs:
            known = output.transformer_id in truth.index
            tripped = bool(truth.loc[output.transformer_id, "tripped"]) if known else False
            early = bool(truth.loc[output.transformer_id, "early"]) if known else False
            counts = counts.add(output.tier == "Critical", tripped, early)
    return [
        Metric(
            "Risk recall, next 24 h scored at 00:00", counts.recall, counts.trips, "share of trips"
        ),
        Metric("Risk recall at >= 12 h lead", counts.recall_early, counts.early_trips, "share"),
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
VALUE_COLUMNS = 4  # baseline, current, new, baseline on the new forecasts (risk only)


def run(domain: str, strategies: list[str], data: Dataset, settings: MlSettings) -> list[str]:
    """Markdown rows comparing each strategy with the domain's baseline.

    Risk: each scorer reads the forecasts of the forecaster it was trained on (its metadata); the
    baseline reads the first challenger's, and is repeated on the last challenger's forecasts so a
    gain from better forecasts is told apart from a gain from the scorer.
    """
    baseline = BASELINES[DOMAINS[domain]]
    runs: list[tuple[str, MlSettings]] = []
    if domain == "risk":
        first = risk_forecaster(strategies[0], settings)
        runs.append((baseline, settings.model_copy(update={"forecaster": first})))
        for strategy in strategies:
            forecaster = risk_forecaster(strategy, settings)
            runs.append((strategy, settings.model_copy(update={"forecaster": forecaster})))
        last = risk_forecaster(strategies[-1], settings)
        if last != first:
            runs.append((baseline, settings.model_copy(update={"forecaster": last})))
    else:
        runs = [(name, settings) for name in [baseline, *strategies]]

    results = [RUNNERS[domain](data, name, s) for name, s in runs]
    labels = [f"{name} on {s.forecaster}" if domain == "risk" else name for name, s in runs]
    rows = []
    for i, metric in enumerate(results[0]):
        cells = [
            f"{label}: {result[i].value:.3g}" for label, result in zip(labels, results, strict=True)
        ]
        cells += ["-"] * (VALUE_COLUMNS - len(cells))
        rows.append(
            f"| {domain} | {metric.name} ({metric.unit}) | {' | '.join(cells)} | {metric.n} |"
        )
    return rows


def main() -> None:
    settings = get_ml_settings()
    parser = argparse.ArgumentParser(description="Backtest strategies against their baselines.")
    parser.add_argument("--domain", choices=[*DOMAINS, "all"], default="all")
    parser.add_argument("--strategy", help="one strategy name (default: every challenger)")
    parser.add_argument("--data-dir", type=Path, default=settings.data_dir)
    parser.add_argument("--report", type=Path, default=Path("reports/backtest.md"))
    args = parser.parse_args()

    data = load_dataset(args.data_dir)
    domains = list(DOMAINS) if args.domain == "all" else [args.domain]
    rows = []
    for domain in domains:
        strategies = [args.strategy] if args.strategy else CHALLENGERS[domain]
        rows += run(domain, strategies, data, settings)

    report = "\n".join(
        [
            "# Backtest (Simulated data)",
            "",
            f"Data: `{args.data_dir}`, held-out last {HOLDOUT_DAYS} days. Every number is from simulated data.",
            "Columns: baseline, current challenger, new challenger; risk adds the baseline on the new",
            "challenger's forecasts. Weather is the simulated day-ahead forecast issued by 00:00.",
            "",
            "| Domain | Metric | Baseline | Current | New | Baseline, new forecasts | n |",
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
