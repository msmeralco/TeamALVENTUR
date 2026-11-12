"""The dashboard rules table and its measured inputs. Pure functions, no I/O."""

import math
from collections.abc import Hashable
from typing import Any

import pandas as pd
import pytest

from silip.dashboard.domain import (
    CLAMP_OFFLINE_SHARE,
    EV_STEP_KW,
    MIN_TRUST_REPORTING,
    TARGET_COVERAGE,
    UPGRADE_DAYS_OF_7,
    clamp_health,
    clamps_to_target,
    elevated_days,
    evening_step_kw,
    heat_peak,
    offline_share,
    open_outage_ids,
    recommend_action,
    rule_drivers,
)
from silip_ml.risk.domain import Tier

TRUSTED = MIN_TRUST_REPORTING
THIN = MIN_TRUST_REPORTING - 0.01
AS_OF = pd.Timestamp("2026-04-21 23:45", tz="Asia/Manila")


def action(tier: Tier = "OK", reporting=1.0, offline=0.0, outage=False, days=0, step=None):
    return recommend_action(tier, reporting, offline, outage, days, step)


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"tier": "Critical", "reporting": TRUSTED}, "Inspect before peak"),
        # A crew is already out for the outage, so no separate inspection.
        ({"tier": "Critical", "reporting": TRUSTED, "outage": True}, "Monitor"),
        ({"tier": "Critical", "reporting": THIN}, "Add clamps"),
        ({"tier": "Watch", "reporting": THIN}, "Add clamps"),
        ({"tier": "OK", "reporting": THIN}, "Monitor"),
        ({"tier": "Watch", "reporting": THIN, "offline": CLAMP_OFFLINE_SHARE + 0.01}, "Fix clamps"),
        ({"offline": CLAMP_OFFLINE_SHARE}, "Monitor"),  # at the threshold is not over it
        ({"days": UPGRADE_DAYS_OF_7}, "Plan upgrade"),
        ({"days": UPGRADE_DAYS_OF_7 - 1}, "Monitor"),
        ({"step": EV_STEP_KW + 0.1}, "Plan upgrade"),
        ({"step": EV_STEP_KW}, "Monitor"),
        ({"tier": "Watch", "reporting": TRUSTED}, "Monitor"),
    ],
)
def test_rules_table(kwargs, expected):
    assert action(**kwargs) == expected


def test_inspect_wins_over_every_other_rule():
    busy = action(tier="Critical", reporting=1.0, offline=0.9, days=7, step=EV_STEP_KW * 2)
    assert busy == "Inspect before peak"


def test_clamps_to_target_counts_online_clamps_and_never_goes_negative():
    assert clamps_to_target(40, 10) == math.ceil(TARGET_COVERAGE * 40) - 10
    assert clamps_to_target(40, 40) == 0
    assert clamps_to_target(0, 0) == 0


def test_clamp_health_reports_online_homes_and_offline_share():
    health = clamp_health(homes=20, clamps_installed=10, clamps_online=7)
    assert (health.homes_reporting, health.reporting_pct) == (7, 0.35)
    assert offline_share(health) == pytest.approx(0.3)
    assert clamp_health(0, 0, 0).reporting_pct == 0.0
    assert offline_share(clamp_health(5, 0, 0)) == 0.0


def test_open_outages_are_started_and_not_yet_restored():
    outages = pd.DataFrame(
        {
            "transformer_id": ["T-open", "T-restored", "T-future", "T-unknown-end"],
            "start_ts": [AS_OF - pd.Timedelta(hours=1)] * 2
            + [AS_OF + pd.Timedelta(hours=1), AS_OF - pd.Timedelta(days=1)],
            "duration_min": [120.0, 30.0, 60.0, None],
        }
    )
    assert open_outage_ids(outages, AS_OF) == {"T-open", "T-unknown-end"}


def _evenings(kw_by_day: dict[int, float]) -> pd.DataFrame:
    """One 21:00 reading per day before AS_OF (day 1 = yesterday)."""
    rows = [
        {
            "transformer_id": "T-1",
            "ts": AS_OF.normalize() - pd.Timedelta(days=day) + pd.Timedelta(hours=21),
            "transformer_kw": kw,
        }
        for day, kw in kw_by_day.items()
    ]
    return pd.DataFrame(rows)


def test_evening_step_is_last_week_minus_the_three_weeks_before():
    history = _evenings({day: (12.0 if day <= 6 else 5.0) for day in range(1, 28)})
    noon = history.assign(ts=history["ts"] - pd.Timedelta(hours=9), transformer_kw=99.0)
    step = evening_step_kw(pd.concat([history, noon]), AS_OF)
    assert step == {"T-1": pytest.approx(7.0)}
    assert evening_step_kw(_evenings({1: 10.0}), AS_OF) == {}  # no baseline weeks


def test_elevated_days_counts_days_whose_measured_peak_reached_watch():
    transformers = pd.DataFrame({"transformer_id": ["T-1"], "rated_kva": [10.0]})
    # 10 kVA x 0.9 = 9 kW usable; 8.5 kW is 94% (Watch level), 5 kW is 56%.
    history = _evenings({1: 8.5, 2: 8.5, 3: 5.0, 4: 8.5, 9: 8.5})
    assert elevated_days(history, transformers, AS_OF) == {"T-1": 3}


def test_heat_peak_reads_one_cell_inside_the_window():
    weather = pd.DataFrame(
        {
            "cell_id": ["A", "A", "A", "B"],
            "ts": [AS_OF + pd.Timedelta(hours=h) for h in (1, 2, 30)] + [AS_OF],
            "heat_index_c": [35.0, 38.0, 45.0, 50.0],
        }
    )
    assert heat_peak(weather, "A", AS_OF, AS_OF + pd.Timedelta(hours=24)) == (
        38.0,
        AS_OF + pd.Timedelta(hours=2),
    )
    assert heat_peak(weather, "C", AS_OF, AS_OF + pd.Timedelta(hours=24)) is None


def test_rule_drivers_follow_the_rule_reasons_without_contributions():
    row: dict[Hashable, Any] = {"peak_load_pct": 1.12, "hours_over_100": 2.5, "coverage_pct": 0.4}
    reasons = ["Peak forecast 112% of rating at 20:15", "Above 100% for 2.5 h", "40% metered"]
    drivers = rule_drivers(row, reasons)
    assert [d.feature for d in drivers] == ["peak_load_pct", "hours_over_100", "coverage_pct"]
    assert [d.label for d in drivers] == reasons
    assert [d.value for d in drivers] == [112.0, 2.5, 40.0]
    assert all(d.contribution is None for d in drivers)
    calm = rule_drivers({**row, "hours_over_100": 0.0}, [reasons[0], reasons[2]])
    assert [d.feature for d in calm] == ["peak_load_pct", "coverage_pct"]
