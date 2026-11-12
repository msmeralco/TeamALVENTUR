---
name: run-backtest
description: Run SILIP's backtests, add a strategy to them, compare a strategy to its baseline, and report the numbers. Use whenever a model, threshold or simulator changes, or when numbers are needed for the pitch or docs.
---

Read first: the `silip-domain` skill (formulas and metrics).

# Running
- All domains, baselines vs configured strategies: `make backtest`.
- One domain: `uv run python -m silip_ml.core.backtest --domain risk --strategy lightgbm`.
- Domains and baselines: `load` → `seasonal_naive`, `risk` → `rules`, `outages.locate` → `nearest_report`, `outages.eta` → `median_by_cause`.
- Split by time: the last 7 days are held out. Never shuffle.
- Data comes from `make sim` (fixed seed). Change the seed only to test stability, and say so.

# Adding a strategy
1. Add one file in `ml/src/silip_ml/<domain>/` implementing the domain's `Protocol`.
2. Register it: `@register("<task>", "<name>")`.
3. Add a test in `tests/ml/<domain>/` that runs it on a tiny simulated set.
4. `make backtest`. The backtest picks it up by name; no other edits.

# Report format (paste into PRs and docs)
| Metric | Baseline | Strategy | n |
|---|---|---|---|
| Risk recall at ≥12 h lead | | | failures |
| False alarms per transformer-month | | | transformer-months |
| Load MAE (kW) | | | intervals |
| Outage locate error, median (m) | | | outages |
| ETA P10 to P90 coverage (%) | | | outages |

Label the table "Simulated" while the data is simulated. A change that lowers risk recall does not ship, even if other metrics improve. Ask the `evaluator` subagent to explain regressions.
