"""NOAA heat index and weather cells.

Reference values are rows of the NWS heat index chart (°F, rounded):
https://www.weather.gov/safety/heat-index and the equation page
https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml
[VERIFY] chart cells were transcribed by hand; NOAA states the regression is within ±1.3 °F of
the chart, so each check allows 1 °F after rounding.
"""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from silip_ml.weather import WEATHER_CELL_DEG, cell_id, heat_index_c


def _f_to_c(f: float) -> float:
    return (f - 32) * 5 / 9


@pytest.mark.parametrize(
    ("temp_f", "rh", "chart_f"),
    [
        (80, 40, 80),
        (86, 50, 88),
        (90, 40, 91),
        (90, 50, 95),
        (90, 60, 100),
        (90, 70, 106),
        (90, 80, 113),
        (90, 90, 122),
        (96, 50, 108),
        (96, 60, 116),
        (100, 40, 109),
        (100, 50, 118),
        (100, 60, 129),
    ],
)
def test_heat_index_matches_noaa_chart(temp_f: float, rh: float, chart_f: float) -> None:
    got_f = heat_index_c(_f_to_c(temp_f), rh) * 9 / 5 + 32
    assert abs(round(got_f) - chart_f) <= 1


def test_simple_formula_below_80f() -> None:
    # Steadman's simple formula: 0.5 * (T + 61 + (T - 68) * 1.2 + RH * 0.094) = 69.05 °F.
    assert heat_index_c(_f_to_c(70), 50) == pytest.approx(_f_to_c(69.05))


def test_noaa_adjustments() -> None:
    # RH < 13% at 95 °F subtracts (13 - RH) / 4 * sqrt((17 - |T - 95|) / 17) = 0.75 °F.
    # RH > 85% at 85 °F adds (RH - 85) / 10 * (87 - T) / 5 = 0.2 °F.
    def rothfusz(t: float, rh: float) -> float:
        return (
            -42.379 + 2.04901523 * t + 10.14333127 * rh - 0.22475541 * t * rh
            - 0.00683783 * t * t - 0.05481717 * rh * rh + 0.00122874 * t * t * rh
            + 0.00085282 * t * rh * rh - 0.00000199 * t * t * rh * rh
        )  # fmt: skip

    assert heat_index_c(_f_to_c(95), 10) == pytest.approx(_f_to_c(rothfusz(95, 10) - 0.75))
    assert heat_index_c(_f_to_c(85), 90) == pytest.approx(_f_to_c(rothfusz(85, 90) + 0.2))


def test_heat_index_is_vectorised() -> None:
    temps = np.array([25.0, 30.0, 35.0])
    out = heat_index_c(temps, 70.0)
    assert out.shape == (3,)
    assert out[0] == pytest.approx(heat_index_c(25.0, 70.0))


def test_cell_id() -> None:
    assert WEATHER_CELL_DEG == 0.1
    assert cell_id(14.6, 121.0) == "14.65_121.05"  # 14.6 / 0.1 is 145.999... in floats
    assert cell_id(14.5915, 121.0673) == "14.55_121.05"
    assert cell_id(14.5999, 121.0999) == cell_id(14.5001, 121.0001)


def test_notebook_copy_agrees() -> None:
    """notebooks/_weather.py (simulator) must match silip_ml.weather (inference)."""
    path = Path(__file__).parents[2] / "notebooks" / "_weather.py"
    spec = importlib.util.spec_from_file_location("notebook_weather", path)
    assert spec is not None and spec.loader is not None
    nb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(nb)
    temps, rh = np.meshgrid(np.linspace(15, 45, 61), np.linspace(5, 100, 39))
    np.testing.assert_array_equal(nb.heat_index_c(temps, rh), heat_index_c(temps, rh))
    assert nb.cell_id(14.5915, 121.0673) == cell_id(14.5915, 121.0673)
    heat = heat_index_c(temps, rh)
    np.testing.assert_allclose(nb.heat_index_c(nb.temperature_for(heat, rh), rh), heat, atol=1e-6)
