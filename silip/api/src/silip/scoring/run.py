"""Run one scoring job locally: `python -m silip.scoring.run` (uses DATA_SOURCE and the Neon URL)."""

from __future__ import annotations

import time

from silip.scoring.handler import utc_now
from silip.scoring.service import run_once
from silip.shared.config import get_settings
from silip.shared.deps import get_data_source, get_score_store


def main() -> None:
    settings = get_settings()
    store = get_score_store(settings)
    if store is None:
        print("status=skipped (DATA_SOURCE=simulated has no score store)")
        return
    started = time.perf_counter()
    result = run_once(
        get_data_source(settings), store, settings.forecaster, settings.risk_scorer, utc_now
    )
    seconds = time.perf_counter() - started
    print(
        f"status={result.status} run_id={result.run_id} transformers={result.transformers}"
        f" seconds={seconds:.1f}"
    )


if __name__ == "__main__":
    main()
