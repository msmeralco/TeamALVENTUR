"""Maps config names to strategy classes, one table per task.

Strategies register themselves with `@register(task, name)`. Domain packages are imported on
first lookup so that adding a strategy never means editing this file.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any, Literal, TypeVar

Task = Literal["forecaster", "risk_scorer", "outage_locator", "eta_estimator"]
TASKS: tuple[Task, ...] = ("forecaster", "risk_scorer", "outage_locator", "eta_estimator")

BASELINES: dict[Task, str] = {
    "forecaster": "seasonal_naive",
    "risk_scorer": "rules",
    "outage_locator": "nearest_report",
    "eta_estimator": "median_by_cause",
}

# Importing these packages runs every @register decorator.
_STRATEGY_PACKAGES = ("silip_ml.load", "silip_ml.risk", "silip_ml.outages")

_registry: dict[Task, dict[str, type]] = {task: {} for task in TASKS}

T = TypeVar("T", bound=type)


class UnknownStrategyError(KeyError):
    """Raised when config names a strategy that is not registered."""


def register(task: Task, name: str) -> Callable[[T], T]:
    """Class decorator: make a strategy available as `name` for `task`."""

    def decorator(cls: T) -> T:
        if name in _registry[task]:
            raise ValueError(f"{task} strategy {name!r} is registered twice")
        _registry[task][name] = cls
        return cls

    return decorator


def _load_strategies() -> None:
    for package in _STRATEGY_PACKAGES:
        importlib.import_module(package)


def names(task: Task) -> list[str]:
    """Registered strategy names for `task`, sorted."""
    _load_strategies()
    return sorted(_registry[task])


def create(task: Task, name: str, **kwargs: Any) -> Any:
    """Instantiate the strategy registered as `name` for `task`.

    Raises:
        UnknownStrategyError: with the valid names, if `name` is not registered.
    """
    _load_strategies()
    try:
        cls = _registry[task][name]
    except KeyError:
        valid = ", ".join(sorted(_registry[task]))
        raise UnknownStrategyError(f"unknown {task} {name!r}; choose one of: {valid}") from None
    return cls(**kwargs)
