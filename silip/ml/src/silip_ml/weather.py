"""Weather helpers shared by the simulator, the weather adapters and the features.

`heat_index_c` is the NOAA/NWS heat index (Rothfusz regression with NOAA's adjustments, Steadman's
simple formula when the result is below 80 °F):
https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml
`notebooks/_weather.py` holds the same definitions for the simulator; `tests/ml/test_weather.py`
checks that the two agree.
"""

from __future__ import annotations

import math
from typing import overload

import numpy as np

WEATHER_CELL_DEG = 0.1  # [VERIFY] against the resolution of the Open-Meteo model we query


def _c_to_f(c: np.ndarray) -> np.ndarray:
    return c * 9.0 / 5.0 + 32.0


def _f_to_c(f: np.ndarray) -> np.ndarray:
    return (f - 32.0) * 5.0 / 9.0


@overload
def heat_index_c(temp_c: float, rh_pct: float) -> float: ...
@overload
def heat_index_c(temp_c: np.ndarray, rh_pct: np.ndarray | float) -> np.ndarray: ...
def heat_index_c(temp_c: float | np.ndarray, rh_pct: float | np.ndarray) -> float | np.ndarray:
    """NOAA heat index in °C from air temperature (°C) and relative humidity (%)."""
    t = _c_to_f(np.asarray(temp_c, dtype=float))
    rh = np.asarray(rh_pct, dtype=float)
    simple = 0.5 * (t + 61.0 + (t - 68.0) * 1.2 + rh * 0.094)
    rothfusz = (
        -42.379
        + 2.04901523 * t
        + 10.14333127 * rh
        - 0.22475541 * t * rh
        - 0.00683783 * t * t
        - 0.05481717 * rh * rh
        + 0.00122874 * t * t * rh
        + 0.00085282 * t * rh * rh
        - 0.00000199 * t * t * rh * rh
    )
    dry = (rh < 13) & (t >= 80) & (t <= 112)
    rothfusz -= np.where(
        dry, (13 - rh) / 4 * np.sqrt(np.clip(17 - np.abs(t - 95), 0, None) / 17), 0.0
    )
    humid = (rh > 85) & (t >= 80) & (t <= 87)
    rothfusz += np.where(humid, (rh - 85) / 10 * ((87 - t) / 5), 0.0)
    result = _f_to_c(np.where((simple + t) / 2 < 80, simple, rothfusz))
    return float(result) if result.ndim == 0 else result


def cell_id(lat: float, lon: float) -> str:
    """Weather cell holding a point, named by its centre, e.g. `14.55_121.05`."""

    def centre(value: float) -> float:
        # round() guards against 14.6 / 0.1 = 145.999...
        index = math.floor(round(value / WEATHER_CELL_DEG, 9))
        return (index + 0.5) * WEATHER_CELL_DEG

    return f"{centre(lat):.2f}_{centre(lon):.2f}"
