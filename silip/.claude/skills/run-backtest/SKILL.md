---
name: run-backtest
description: Run SILIP's backtests, add a strategy to them, compare a strategy to its baseline, and report the numbers. Use whenever a model, threshold or simulator changes, or when numbers are needed for the pitch or docs.
---

Read first: the `silip-domain` skill (formulas and metrics).

# Running
- All domains, each baseline vs its challenger (`lightgbm`, `lightgbm`, `dbscan`, `quantile_lgbm`): `make backtest`. Trained challengers are the exported artifacts in `models/`; the backtest refuses one whose training window reaches the held-out days (`LeakageError`).
- Risk rows score the same forecasts for both scorers: the forecaster named in the risk artifact's `metadata.json`.
- One domain: `uv run python -m silip_ml.backtest --domain risk --strategy lightgbm`. Report: `reports/backtest.md`.
- Domains and baselines: `load` → `seasonal_naive`, `risk` → `rules`, `locate` → `nearest_report`, `eta` → `median_by_cause`.
- Split by time: the last 7 days are held out. Never shuffle.
- Data comes from `make sim` (`notebooks/00`, dev scale, seed 7). Change the seed only to test stability, and say so. After new data, re-run notebooks 04 to 06 (`make notebooks`) so the artifacts are trained on the same data; `metadata.json` records the data file's SHA-256.

# Adding a strategy
1. Train and export it in a notebook (`models/<task>/<name>/` with `model.txt`, `metadata.json`, `parity/`), then add one file in `ml/src/silip_ml/<domain>/` that loads it and implements the domain's `Protocol` (predict only).
2. Register it: `@register("<task>", "<name>")`.
3. Add a test in `tests/ml/<domain>/` that runs it on `tests/fixtures/sim`, and a parity test like `tests/ml/test_parity.py`.
4. `make backtest`. The backtest picks it up by name; no other edits.

# Report format (paste into PRs and docs)
| Metric | Baseline | Strategy | n |
|---|---|---|---|
| Risk recall, next 24 h scored at 00:00 (target: at ≥12 h lead) | | | trips |
| False alarms per transformer-month | | | transformer-months |
| Load MAE (kW) | | | intervals |
| Outage locate error, median (m) | | | outages |
| ETA P10 to P90 coverage (%) | | | outages |

Label the table "Simulated" while the data is simulated. A change that lowers risk recall does not ship, even if other metrics improve. Ask the `evaluator` subagent to explain regressions.
