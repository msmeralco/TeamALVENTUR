# notebooks

Everything before inference lives here: mock data, data understanding, EDA, preprocessing, features, training, tuning, evaluation and export. `silip_ml` only loads what `06` exports. Notebooks never import `silip_ml`.

Run in order (each one reads what the one before wrote). Times are one laptop run at dev scale.

| Notebook | Answers | Key finding (Simulated) | Time |
|---|---|---|---|
| `00_generate_mock_data` | What data do we model on? Writes `data/sim/` (or `tests/fixtures/sim` with `SIM_SCALE=test`). | 50 transformers × 56 days on real OSM sites, every scenario a named, sourced knob (`data/README.md`). | ~20 s |
| `01_data_overview` | What is in each table, and how clean is it? | About 1% of intervals missing, exactly where outages are; clamp reporting drifts with late installs and dead clamps; small jumpers stay under the 15% flag. | ~20 s |
| `02_eda` | What drives load, and what comes before a trip? | Peak load tracks heat index (r 0.65); EVs add a later 8 PM peak, solar a midday dip; transformers that trip were above 110% on days before. | ~90 s |
| `03_features_and_preprocessing` | Which inputs and which gap/outlier handling? (time-series CV) | Lags (1, 2, 7 days) + calendar win; gaps kept as missing; no clipping. A day-ahead heat index would cut error most, but scoring has no weather feed. | ~70 to 95 s |
| `04_train_load_forecast` | Which forecaster, which parameters? | Tuned LightGBM cuts validation MAE 43% vs seasonal naive, in every hour, rating and scenario group. | ~40 to 60 s |
| `05_train_risk_model` | Can a model beat the rules on recall without more false alarms? | Trained on out-of-sample forecast features; on validation it matches rules recall with slightly fewer false alarms. | ~30 to 45 s |
| `06_evaluate_and_export` | Do the chosen models win on the held-out week? Export them. | Load MAE 4.75 vs 7.82 kW: kept. Risk recall 100% vs 96% but 9.3 vs 8.7 false alarms per transformer-month: exported as a candidate (`kept: false`), rules stay default. | ~25 s |

Shared code sits in small modules next to the notebooks: `_data.py` (paths, loading, holidays, holdout split), `_style.py` (Plotly template; every chart says "Simulated data"), `_features.py` (feature definitions), `_models.py` (training helpers). `results/*.json` carries each notebook's choice to the next.

## Running
- One notebook: `uv run --group notebooks jupyter nbconvert --to notebook --execute --inplace notebooks/04_train_load_forecast.ipynb`
- All, in order: `make notebooks`. Mock data only: `make sim` (`SIM_SCALE=test|dev|large|xlarge`).
- Charts render as PNG so they show on GitHub; set `SILIP_PLOTLY_RENDERER=notebook` for interactive charts.

## Rules
- Time-based splits only, never shuffled. The last 7 days are held out and used once, in `06`.
- A model is kept only if it beats its baseline there.
- Changing a feature means changing `_features.py` and `ml/src/silip_ml/features.py`, re-running `04` to `06`, and committing `models/` with its new parity sample. `tests/ml/test_parity.py` fails otherwise.
