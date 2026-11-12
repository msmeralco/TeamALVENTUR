"""Heat index and weather cells for the simulator. No silip_ml import: notebooks stand alone.

Same definitions as `silip_ml/weather.py` (NOAA heat index:
https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml); `tests/ml/test_weather.py` checks
that the two agree. The simulator draws heat index first, so `temperature_for` inverts it.
"""

from __future__ import annotations

import math

import numpy as np

WEATHER_CELL_DEG = 0.1  # [VERIFY] against the resolution of the Open-Meteo model we query


def heat_index_c(temp_c, rh_pct) -> np.ndarray:
    """NOAA heat index in °C from air temperature (°C) and relative humidity (%), elementwise."""
    t = np.asarray(temp_c, dtype=float) * 9.0 / 5.0 + 32.0
    rh = np.asarray(rh_pct, dtype=float)
    simple = 0.5 * (t + 61.0 + (t - 68.0) * 1.2 + rh * 0.094)
    rothfusz = (
        -42.379 + 2.04901523 * t + 10.14333127 * rh - 0.22475541 * t * rh - 0.00683783 * t * t
        - 0.05481717 * rh * rh + 0.00122874 * t * t * rh + 0.00085282 * t * rh * rh
        - 0.00000199 * t * t * rh * rh
    )
    dry = (rh < 13) & (t >= 80) & (t <= 112)
    rothfusz -= np.where(dry, (13 - rh) / 4 * np.sqrt(np.clip(17 - np.abs(t - 95), 0, None) / 17), 0.0)
    humid = (rh > 85) & (t >= 80) & (t <= 87)
    rothfusz += np.where(humid, (rh - 85) / 10 * ((87 - t) / 5), 0.0)
    return (np.where((simple + t) / 2 < 80, simple, rothfusz) - 32.0) * 5.0 / 9.0


def temperature_for(heat_c, rh_pct, low_c: float = 5.0, high_c: float = 50.0) -> np.ndarray:
    """Air temperature (°C) whose NOAA heat index at `rh_pct` equals `heat_c`, by bisection."""
    heat_c = np.asarray(heat_c, dtype=float)
    low, high = np.full(heat_c.shape, low_c), np.full(heat_c.shape, high_c)
    for _ in range(50):
        mid = (low + high) / 2
        above = heat_index_c(mid, rh_pct) > heat_c
        high, low = np.where(above, mid, high), np.where(above, low, mid)
    return (low + high) / 2


def cell_id(lat: float, lon: float) -> str:
    """Weather cell holding a point, named by its centre, e.g. `14.55_121.05`."""

    def centre(value: float) -> float:
        index = math.floor(round(value / WEATHER_CELL_DEG, 9))
        return (index + 0.5) * WEATHER_CELL_DEG

    return f"{centre(lat):.2f}_{centre(lon):.2f}"
