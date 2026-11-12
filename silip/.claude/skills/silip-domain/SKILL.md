---
name: silip-domain
description: SILIP formulas, simulation recipe and evaluation metrics. Use for data, aggregation, simulation and backtest work.
---
## Aggregation (per transformer T, 15-min interval)
- `measured_kw` = sum of `power_kw` over clamped or smart-metered homes on T
- `estimated_kw` = unmetered homes' monthly kWh spread by a heat-adjusted daily shape learned from metered homes
- `load_pct` = (measured + estimated) / (rated_kva × 0.9); `coverage_pct` = metered homes / all homes
- Jumper gap (only with a check meter): (check_kwh − sum of homes) / check_kwh; flag if >15% for 7+ days and coverage ≥80%

## Simulation recipe (`notebooks/00_generate_mock_data.ipynb`, knobs in `data/README.md`)
Ratings {25, 37.5, 50, 75, 100} kVA; 20 to 60 homes each, sized to a loading class; base 0.2 to 0.6 kW; evening aircon scaled by heat index; weekends and holidays add daytime load; hot spells, rain and a typhoon; homes adopt EVs (3.3 to 7.4 kW from 8 PM) over the run; some homes have rooftop solar; some transformers get unmetered jumper load (visible only with a check meter); clamps have opt-in coverage, late installs, dead clamps, Wi-Fi drops, ±1% noise; trips when true load >110% for 3+ h on 3+ days; restoration lognormal, median 2 to 4 h. Scales: `test`, `dev` (50 transformers, 56 days), `large` (2,000 × 14 days), `xlarge` (4,000 × 14 days).

## Training and inference
Models are trained and exported in `notebooks/04` to `06`; `silip_ml` only loads `models/<task>/<name>/` and predicts. Load features are at least one day old (lags 1, 2, 7 days plus calendar), so one call forecasts 24 h for every transformer. The risk model trains on features of out-of-sample day-ahead forecasts, labeled by the trip rule on true load.

## Metrics (backtest: 50 transformers, 56 days, last 7 held out)
Recall at ≥12 h lead · false alarms per transformer-month · median locate time · ETA P10 to P90 coverage. Always vs the baseline rule "load >100% for 2 h". Label results "Simulated".
