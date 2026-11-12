---
name: silip-domain
description: SILIP formulas, simulation recipe and evaluation metrics. Use for data, aggregation, simulation and backtest work.
---
## Aggregation (per transformer T, 15-min interval)
- `measured_kw` = sum of `power_kw` over clamped or smart-metered homes on T
- `estimated_kw` = unmetered homes' monthly kWh spread by a heat-adjusted daily shape learned from metered homes
- `load_pct` = (measured + estimated) / (rated_kva × 0.9); `coverage_pct` = metered homes / all homes
- Jumper gap (only with a check meter): (check_kwh − sum of homes) / check_kwh; flag if >15% for 7+ days and coverage ≥80%

## Simulation recipe
Ratings {25, 37.5, 50, 75, 100} kVA; 20 to 60 homes each; base 0.2 to 0.6 kW; evening aircon scaled by heat index; some homes add EV 3.3 to 7.4 kW from 8 PM; some transformers get unmetered jumper load; trips when load >110% for 3+ h on 3+ days; restoration lognormal, median 2 to 4 h.

## Metrics (backtest: 50 transformers, 30 days, last 7 held out, 10 injected failures)
Recall at ≥12 h lead · false alarms per transformer-month · median locate time · ETA P10 to P90 coverage. Always vs the baseline rule "load >100% for 2 h". Label results "Simulated".
