import pytest

from silip_ml.core.registry import BASELINES, TASKS, UnknownStrategyError, create, names


def test_every_task_has_its_baseline_and_an_alternative():
    for task in TASKS:
        assert BASELINES[task] in names(task)
        assert len(names(task)) >= 2


def test_unknown_strategy_lists_valid_names():
    with pytest.raises(UnknownStrategyError, match="seasonal_naive"):
        create("forecaster", "nope")
