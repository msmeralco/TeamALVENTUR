"""Public, read-only routes for the /demo page. Bench rig (`BENCH-*`) only; anything else is 404."""

from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from silip.bench import service
from silip.bench.domain import BenchSnapshot, NotBenchError
from silip.shared.bench.adapters import NeonBenchReadings
from silip.shared.bench.domain import BenchReadings
from silip.shared.config import get_settings
from silip.shared.db import connect

router = APIRouter(prefix="/api/v1/bench", tags=["bench"])


@lru_cache(maxsize=1)
def _readings() -> NeonBenchReadings:
    return NeonBenchReadings(lambda: connect(get_settings()))


def get_bench_readings() -> BenchReadings:
    """One reader per process, so its database connection is reused across polls."""
    return _readings()


Readings = Annotated[BenchReadings, Depends(get_bench_readings)]


@router.get("", response_model=BenchSnapshot)
def bench(readings: Readings) -> BenchSnapshot:
    """Public: the bench rig's mock homes and both transformers, from the last 3 minutes."""
    return service.bench_snapshot(readings, datetime.now(UTC))


@router.get("/{transformer_id}", response_model=BenchSnapshot)
def bench_transformer(transformer_id: str, readings: Readings) -> BenchSnapshot:
    """Public: one bench transformer. Refuses every transformer that is not on the bench."""
    try:
        return service.bench_snapshot(readings, datetime.now(UTC), transformer_id)
    except NotBenchError as error:
        raise HTTPException(status_code=404, detail="Not a bench transformer") from error
