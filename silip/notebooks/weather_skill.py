"""Measure real day-ahead forecast skill for Metro Manila from Open-Meteo (calibrates the simulator).

    uv run python notebooks/weather_skill.py [--cache D:/tmp/openmeteo] [--start 2025-11-01] [--end 2026-10-31]

Compares Open-Meteo's archived forecasts (Previous Runs API, `best_match`, the same default model the
scoring Lambda reads) with the ERA5 reanalysis (Archive API) on the hour. ERA5 is itself a model, so
this is "forecast vs reanalysis", not "vs observations". `_previous_dayN` is the value the run made
about N x 24 h earlier forecast for that hour (lead about N x 24 to N x 24 + 6 h). The simulator issues at
00:00 Manila for the next 72 h from runs started 6 to 12 h before, so its lead day 0 / 1 / 2 is
compared with previous_day1 / 2 / 3 (a slightly conservative match).

The simulator's forecast error is: temperature = truth + one offset per issue and lead day
(sd = forecast_error_sd_c x (1 + growth x lead day)) + hourly jitter (sd = forecast_error_sd_c / 3);
humidity = truth + one offset per lead day (sd = forecast_error_sd_rh_pct). So the matching real
statistics are the SD of the daily-mean error across days and the SD of the hourly error around it.

Raw JSON is cached outside the repo (default D:/tmp/openmeteo) and never committed. Results go to
notebooks/results/weather_skill.json. Stdlib urllib; certifi's CA bundle is used when installed
(some Windows Python builds ship an outdated store).
"""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _weather import heat_index_c  # noqa: E402  (same NOAA formula as silip_ml.weather)

POINTS = {"manila_14.60_121.00": (14.60, 121.00), "qc_14.65_121.05": (14.65, 121.05)}
PREVIOUS_RUNS = "https://previous-runs-api.open-meteo.com/v1/forecast"
ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
DAYS = (1, 2, 3)  # previous_dayN compared with simulator lead day N - 1
HOT_MONTHS = (3, 4, 5)
SIM = {
    "forecast_error_sd_c": 1.0,
    "forecast_error_growth_per_day": 0.5,
    "forecast_error_sd_rh_pct": 5.0,
}


def _context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def fetch(url: str, params: dict[str, str], cache: Path) -> dict:
    query = urllib.parse.urlencode(params)
    name = f"{url.split('//')[1].split('.')[0]}_{params['latitude']}_{params['longitude']}_{params['start_date']}_{params['end_date']}.json"
    path = cache / name
    if not path.exists():
        request = f"{url}?{query}"  # fixed https Open-Meteo hosts only
        with urllib.request.urlopen(request, timeout=60, context=_context()) as response:  # noqa: S310
            path.write_bytes(response.read())
    return json.loads(path.read_text(encoding="utf-8"))


def point_frame(lat: float, lon: float, start: str, end: str, cache: Path) -> pd.DataFrame:
    common = {
        "latitude": str(lat),
        "longitude": str(lon),
        "start_date": start,
        "end_date": end,
        "timezone": "Asia/Manila",
    }
    variables = [
        f"{v}_previous_day{d}" for d in DAYS for v in ("temperature_2m", "relative_humidity_2m")
    ]
    fcst = fetch(PREVIOUS_RUNS, {**common, "hourly": ",".join(variables)}, cache)["hourly"]
    arch = fetch(ARCHIVE, {**common, "hourly": "temperature_2m,relative_humidity_2m"}, cache)[
        "hourly"
    ]
    frame = pd.DataFrame(fcst).merge(pd.DataFrame(arch), on="time")
    frame["time"] = pd.to_datetime(frame["time"])
    return frame


def skill(frame: pd.DataFrame, day: int) -> dict[str, float]:
    t_f, rh_f = (
        frame[f"temperature_2m_previous_day{day}"],
        frame[f"relative_humidity_2m_previous_day{day}"],
    )
    ok = (
        t_f.notna()
        & rh_f.notna()
        & frame["temperature_2m"].notna()
        & frame["relative_humidity_2m"].notna()
    )
    f = frame[ok]
    t_e = f[f"temperature_2m_previous_day{day}"] - f["temperature_2m"]
    rh_e = f[f"relative_humidity_2m_previous_day{day}"] - f["relative_humidity_2m"]
    hi_f = heat_index_c(
        f[f"temperature_2m_previous_day{day}"], f[f"relative_humidity_2m_previous_day{day}"]
    )
    hi_t = heat_index_c(f["temperature_2m"], f["relative_humidity_2m"])
    hi_e = pd.Series(hi_f - hi_t, index=f.index)
    date = f["time"].dt.date
    daily_t = t_e.groupby(date).mean()
    daily_rh = rh_e.groupby(date).mean()
    hi_max_e = (
        pd.Series(hi_f, index=f.index).groupby(date).max()
        - pd.Series(hi_t, index=f.index).groupby(date).max()
    )
    return {
        "hours": int(ok.sum()),
        "days": int(date.nunique()),
        "temp_bias_c": float(t_e.mean()),
        "temp_sd_c": float(t_e.std()),
        "temp_mae_c": float(t_e.abs().mean()),
        "temp_daily_mean_err_sd_c": float(daily_t.std()),
        "temp_hourly_resid_sd_c": float((t_e - date.map(daily_t)).std()),
        "rh_bias_pct": float(rh_e.mean()),
        "rh_sd_pct": float(rh_e.std()),
        "rh_mae_pct": float(rh_e.abs().mean()),
        "rh_daily_mean_err_sd_pct": float(daily_rh.std()),
        "hi_bias_c": float(hi_e.mean()),
        "hi_sd_c": float(hi_e.std()),
        "hi_mae_c": float(hi_e.abs().mean()),
        "hi_daily_max_bias_c": float(hi_max_e.mean()),
        "hi_daily_max_mae_c": float(hi_max_e.abs().mean()),
        "hi_daily_max_mae_debiased_c": float((hi_max_e - hi_max_e.mean()).abs().mean()),
        "hi_daily_max_p95_abs_c": float(hi_max_e.abs().quantile(0.95)),
        "hi_daily_max_worst_abs_c": float(hi_max_e.abs().max()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache", type=Path, default=Path("D:/tmp/openmeteo"))
    parser.add_argument("--start", default="2025-11-01")
    parser.add_argument("--end", default="2026-10-31")
    parser.add_argument(
        "--out", type=Path, default=Path(__file__).parent / "results" / "weather_skill.json"
    )
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)

    frames = {
        name: point_frame(lat, lon, args.start, args.end, args.cache)
        for name, (lat, lon) in POINTS.items()
    }
    results: dict[str, dict] = {}
    both = pd.concat(frames.values())
    hot = both[both["time"].dt.month.isin(HOT_MONTHS)]  # the simulator's April to May window
    for name, frame in {**frames, "both": both, "both, Mar to May": hot}.items():
        results[name] = {f"previous_day{d} (sim lead day {d - 1})": skill(frame, d) for d in DAYS}
    for name, by_day in results.items():
        print(f"\n{name}")
        print(pd.DataFrame(by_day).round(2).to_string())

    both = results["both, Mar to May"]
    sd0 = both["previous_day1 (sim lead day 0)"]["temp_daily_mean_err_sd_c"]
    sd2 = both["previous_day3 (sim lead day 2)"]["temp_daily_mean_err_sd_c"]
    recommended = {
        "forecast_error_sd_c": round(sd0, 2),
        "forecast_error_growth_per_day": round(max((sd2 / sd0 - 1) / 2, 0.0), 2),
        "forecast_error_sd_rh_pct": round(
            both["previous_day1 (sim lead day 0)"]["rh_daily_mean_err_sd_pct"], 1
        ),
        "note": "Mar to May, both points: sd of the daily-mean temperature / humidity error at simulator lead day 0, and its growth "
        "to lead day 2; the simulator's hourly jitter (sd/3) is checked against temp_hourly_resid_sd_c",
    }
    print("\nrecommended:", recommended)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "source": "Open-Meteo Previous Runs API (best_match) vs Archive API (ERA5 reanalysis); forecast vs reanalysis",
                "period": [args.start, args.end],
                "points": POINTS,
                "simulator_now": SIM,
                "results": results,
                "recommended": recommended,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    np.seterr(all="ignore")
    main()
