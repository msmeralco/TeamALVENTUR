"""Neon implementation of the score store (tables score_run, transformer_score, forecast_point)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict
from datetime import datetime
from typing import Any

import pandas as pd
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from silip.shared.readings.adapters import LOCAL_TZ
from silip.shared.scores.domain import DuplicateRunError, ScoreDetail, ScoreRun, StoredRun
from silip_ml.risk.domain import RiskOutput

RUN_COLUMNS = (
    "run_id, as_of, started_at, finished_at, forecaster, risk_scorer, transformers, is_simulated,"
    " weather_issued_at, weather_status"
)
INSERT_RUN = (
    f"INSERT INTO score_run ({RUN_COLUMNS}, status, error) VALUES (%(run_id)s, %(as_of)s,"  # noqa: S608  (constant columns)
    " %(started_at)s, %(finished_at)s, %(forecaster)s, %(risk_scorer)s, %(transformers)s,"
    " %(is_simulated)s, %(weather_issued_at)s, %(weather_status)s, %(status)s, %(error)s)"
)
SCORE_COLUMNS = (
    "transformer_id",
    "tier",
    "reasons",
    "confidence",
    "peak_load_pct",
    "coverage_pct",
    "is_simulated",
)
DETAIL_COLUMNS = (
    "peak_ts",
    "action",
    "drivers",
    "heat_index_max_c",
    "ev_evening_step_kw",
    "homes_reporting",
    "clamps_installed",
    "clamps_online",
)
INSERT_SCORE = (
    "INSERT INTO transformer_score (run_id, transformer_id, tier, reasons, confidence,"
    " peak_load_pct, coverage_pct, is_simulated, peak_ts, action, drivers, heat_index_max_c,"
    " ev_evening_step_kw, homes_reporting, clamps_installed, clamps_online) VALUES (%(run_id)s,"
    " %(transformer_id)s, %(tier)s, %(reasons)s, %(confidence)s, %(peak_load_pct)s,"
    " %(coverage_pct)s, %(is_simulated)s, %(peak_ts)s, %(action)s, %(drivers)s,"
    " %(heat_index_max_c)s, %(ev_evening_step_kw)s, %(homes_reporting)s, %(clamps_installed)s,"
    " %(clamps_online)s)"
)
COPY_FORECAST = "COPY forecast_point (run_id, transformer_id, ts, kw_pred, is_simulated) FROM STDIN"
LATEST_RUN = (
    f"SELECT {RUN_COLUMNS} FROM score_run WHERE status = 'complete'"  # noqa: S608  (constant columns)
    " ORDER BY as_of DESC, finished_at DESC LIMIT 1"
)
SELECT_SCORES = (
    "SELECT transformer_id, tier, reasons, confidence::float8 AS confidence,"
    " peak_load_pct::float8 AS peak_load_pct, coverage_pct::float8 AS coverage_pct, is_simulated,"
    " peak_ts, action, drivers, heat_index_max_c::float8 AS heat_index_max_c,"
    " ev_evening_step_kw::float8 AS ev_evening_step_kw, homes_reporting, clamps_installed,"
    " clamps_online FROM transformer_score WHERE run_id = %(run_id)s ORDER BY transformer_id"
)
SELECT_FORECAST = (
    "SELECT transformer_id, ts, kw_pred::float8 AS kw_pred, is_simulated FROM forecast_point"
    " WHERE run_id = %(run_id)s ORDER BY transformer_id, ts"
)
HAS_COMPLETE_RUN = (
    "SELECT EXISTS (SELECT 1 FROM score_run WHERE status = 'complete' AND as_of = %(as_of)s"
    " AND forecaster = %(forecaster)s AND risk_scorer = %(risk_scorer)s)"
)
FORECAST_COLUMNS = ["transformer_id", "ts", "kw_pred", "is_simulated"]


def _run_row(run: ScoreRun, status: str, error: str | None) -> dict[str, Any]:
    return asdict(run) | {"status": status, "error": error}


def _score_row(run_id: str, score: RiskOutput, detail: ScoreDetail | None) -> dict[str, Any]:
    """Score columns plus the dashboard columns; runs without details store nulls there."""
    risk = score.model_dump(include=set(SCORE_COLUMNS))
    fields = dict.fromkeys(DETAIL_COLUMNS)
    if detail is not None:
        fields |= detail.model_dump(include=set(DETAIL_COLUMNS))
        fields["drivers"] = Jsonb(detail.model_dump(mode="json")["drivers"])
    return risk | fields | {"run_id": run_id}


def _risk(row: dict[str, Any]) -> RiskOutput:
    """The stored score; fields RiskOutput gained later (peak_ts, drivers) when it has them."""
    fields = set(RiskOutput.model_fields)
    return RiskOutput(**{k: v for k, v in row.items() if k in fields and v is not None})


def _detail(row: dict[str, Any]) -> ScoreDetail | None:
    """None for scores written before the dashboard columns existed (action is null there)."""
    if row.get("action") is None:
        return None
    values = {column: row[column] for column in DETAIL_COLUMNS}
    values["drivers"] = values["drivers"] or []
    return ScoreDetail(transformer_id=row["transformer_id"], **values)


class NeonScoreStore:
    """Insert-only: the app role has SELECT and INSERT on the score tables, nothing else."""

    def __init__(self, connect: Callable[[], psycopg.Connection]) -> None:
        self._connect = connect

    def has_complete_run(self, as_of: datetime, forecaster: str, risk_scorer: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                HAS_COMPLETE_RUN,
                {"as_of": as_of, "forecaster": forecaster, "risk_scorer": risk_scorer},
            ).fetchone()
        return bool(row and row[0])

    def write_run(
        self,
        run: ScoreRun,
        scores: Sequence[RiskOutput],
        forecast: pd.DataFrame,
        details: Sequence[ScoreDetail] = (),
    ) -> None:
        by_id = {detail.transformer_id: detail for detail in details}
        # One transaction: the connection commits on a clean exit and rolls back on any error,
        # so a reader never sees a complete run without all its rows.
        with self._connect() as connection, connection.cursor() as cursor:
            try:
                cursor.execute(INSERT_RUN, _run_row(run, "complete", None))
            except psycopg.errors.UniqueViolation as error:  # score_run_bucket: a parallel run won
                raise DuplicateRunError(run.as_of.isoformat()) from error
            cursor.executemany(
                INSERT_SCORE,
                [
                    _score_row(run.run_id, score, by_id.get(score.transformer_id))
                    for score in scores
                ],
            )
            with cursor.copy(COPY_FORECAST) as copy:
                for row in forecast[FORECAST_COLUMNS].to_dict("records"):
                    copy.write_row(
                        (
                            run.run_id,
                            row["transformer_id"],
                            pd.Timestamp(row["ts"]).to_pydatetime(),
                            float(row["kw_pred"]),
                            bool(row["is_simulated"]),
                        )
                    )

    def write_failed(self, run: ScoreRun, error_class: str) -> None:
        with self._connect() as connection:
            connection.execute(INSERT_RUN, _run_row(run, "failed", error_class))

    def latest_run(self) -> StoredRun | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            run_row = cursor.execute(LATEST_RUN).fetchone()
            if run_row is None:
                return None
            run = ScoreRun(**run_row)
            params = {"run_id": run.run_id}
            score_rows = cursor.execute(SELECT_SCORES, params).fetchall()
            forecast_rows = cursor.execute(SELECT_FORECAST, params).fetchall()
        forecast = pd.DataFrame(forecast_rows, columns=FORECAST_COLUMNS)
        forecast["ts"] = pd.to_datetime(forecast["ts"], utc=True).dt.tz_convert(LOCAL_TZ)
        scores = tuple(map(_risk, score_rows))
        details = tuple(d for d in map(_detail, score_rows) if d is not None)
        return StoredRun(run, scores, forecast, details)
