import numpy as np
import pytest

from silip_ml.core.registry import create, names
from silip_ml.readings.domain import STEPS_PER_DAY
from silip_ml.risk.domain import is_trip, longest_run


@pytest.mark.parametrize("name", names("risk_scorer"))
def test_scorer_contract(dataset, name):
    """Every scorer gives each transformer a tier, at most 3 reasons, and a labeled result."""
    forecast = create("forecaster", "seasonal_naive").predict(dataset.load, STEPS_PER_DAY)
    outputs = (
        create("risk_scorer", name)
        .fit(dataset.load, dataset.transformers)
        .score(forecast, dataset.transformers)
    )
    assert {o.transformer_id for o in outputs} == set(dataset.transformers["transformer_id"])
    for output in outputs:
        assert output.tier in {"OK", "Watch", "Critical"}
        assert 1 <= len(output.reasons) <= 3
        assert output.is_simulated


def test_trip_needs_three_hours_above_110_percent():
    assert longest_run(np.array([True, True, False, True])) == 2
    assert is_trip(np.full(12, 1.2))
    assert not is_trip(np.full(11, 1.2))
