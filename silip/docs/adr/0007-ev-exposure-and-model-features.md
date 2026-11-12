# 0007. EV exposure, clamp health and model features

- Status: Accepted
- Date: 2026-11-13

## Context
Engineers need to see where EV charging and heat will push load over rating, and how far to trust each estimate. Another session supplies the DOE EV charging station list and EV adoption stats. The current LightGBM risk model is not kept; the rules scorer is in use. Reasons come from rules, and confidence equals coverage.

## Decision
- Map DOE stations to transformers by distance (`EV_STATION_RADIUS_M = 1000` [VERIFY]) into `transformer_ev_exposure`.
- Measure EV charging on each transformer as its evening step: mean kW 20:00 to 24:00 over the last 7 days minus days 8 to 28. This is a plain stand-in for the `ruptures` change point in the spec.
- Use adoption stats only as a labeled planning scenario ("Scenario, not a forecast"), not as a model feature.
- New features: forecast heat index, forecast minus yesterday, rain; risk adds peak heat index, evening step, stations within radius and reporting share.
- Confidence becomes the share of homes reporting (clamp health), not installed coverage.
- Reasons come from LightGBM per-feature contributions (`pred_contrib`), top three, written as plain sentences.
- New strategies are saved under new names. They replace the current ones only if the backtest beats both the current model and the baseline, with the same verdict on a second seed.
- Recommended actions come from a rules table with named constants [VERIFY]: Inspect before peak, Add clamps, Fix clamps, Plan upgrade, Monitor. No "Rebalance": there is no per-phase data.

## Alternatives considered
- Adoption stats as a feature: constant within a city and too few periods to learn from.
- SHAP library: LightGBM's built-in contributions give the same values without a new dependency.

## Consequences
- Easier: one dashboard answers what fails next, why, and what to do.
- Watch: simulated EV homes are unrelated to real station locations, so station proximity will show about zero gain on simulated data; reports say so.
