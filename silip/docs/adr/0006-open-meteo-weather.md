# 0006. Weather from Open-Meteo, fetched server-side

- Status: Accepted
- Date: 2026-11-13

## Context
Notebook 03 found that a day-ahead heat index would cut forecast error the most, but scoring has no weather feed. PAGASA has no free public API. The simulator's weather is the truth that generated load, so training on it leaks the answer.

## Decision
The scoring Lambda fetches Open-Meteo hourly forecasts (temperature, relative humidity, precipitation) for all weather cells in one request, at most once per hour, and stores them insert-only in `weather_hourly` keyed by `issued_at`. Heat index uses the NOAA formula in `silip_ml.weather`. Cells are a 0.1 degree grid [VERIFY]. On failure the run uses the latest stored forecast (marked stale after 6 h [VERIFY]) or the non-weather forecaster; a weather failure never fails a run. Training and backtests use simulated day-ahead forecasts (truth plus error), never the true weather.

## Alternatives considered
- OpenWeatherMap: needs a key in Secrets Manager and has call limits.
- Fetch in the browser: exposes the dependency to every viewer and cannot feed the model.

## Consequences
- Easier: no key, no secret, no IAM change; Lambdas already have egress (no VPC).
- Watch: the free tier is for non-commercial use [VERIFY] terms; a real pilot needs the paid plan. Part of the weather gain on simulated data exists by construction, and reports say so.
