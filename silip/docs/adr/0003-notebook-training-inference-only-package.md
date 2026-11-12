# 0003. Train in notebooks, commit the artifacts, keep `silip_ml` inference-only

- Status: Accepted
- Date: 2026-11-12

## Context
`silip_ml` mixed four jobs: mock data (`readings/simulate.py`), training (each strategy's `.fit()`), inference and the backtest. The API and the scheduled scoring job (ADR 0002) refit LightGBM on every run, so a run's time went mostly to training (forecaster fit 4.4 s + risk fit 11.0 s of 28.6 s at 2,000 transformers × 14 days, measured locally, Simulated) and nothing recorded how a model was chosen. The three notebooks were empty stubs.

## Decision
Numbered, self-contained notebooks (`notebooks/00` to `06`, no `silip_ml` import) own mock data, EDA, preprocessing, features, training, tuning, evaluation and export. They export each kept model to `models/<task>/<name>/`: LightGBM native text (`model.txt`, never pickle), `metadata.json` (features, feature parameters, training window, data seed and SHA-256, metrics, library versions, date) and a `parity/` sample. `silip_ml` loads the artifact, builds features for every transformer at once and predicts in one call; it never trains. Artifacts are committed to git.

Features are written twice (`notebooks/_features.py` to train, `silip_ml/features.py` to serve). The guard is `tests/ml/test_parity.py`: from the exported input rows, `silip_ml` must reproduce the notebook's features and predictions bit for bit. `make backtest` refuses an artifact whose training window reaches the held-out days.

## Alternatives considered
- Keep training inside the scoring job: simplest, but it pays the training cost every 15 minutes, leaves no record of the choice, and the job's window (14 days) is too short to tune on.
- Fit daily in a separate job, store models in S3 or a model registry (MLflow, SageMaker): right once models retrain on live data. Today models train on simulated data by hand, the files are small, and git already gives history and review. Revisit when real clamp data arrives.
- Notebooks import `silip_ml` (the old rule): one copy of the features, but notebooks then depend on package internals, and training code stays in the package. The parity test gives the safety of one copy without that coupling.
- Pickle or joblib: smaller code, but unsafe to load and tied to library versions. LightGBM's text format is readable and diffable.

## Consequences
- Scoring is predict-only and batched (one LightGBM call for all transformers). Measured locally, one process, lightgbm + lightgbm, Simulated: 2,000 transformers × 14 days 32.4 s → 3.1 s (fit + forecast + score 30.2 s → 1.4 s), peak 644 → 584 MB; 4,000 × 14 days 67.7 s → 6.9 s, peak 1,126 → 1,003 MB. Reading the CSVs is now most of the run and sets the memory peak. The `fit` method stays on the `Forecaster` and `RiskScorer` ports as a no-op until the API stops calling it.
- Changing a feature means editing both files, re-running notebooks 04 to 06 and committing the new artifacts with their parity sample; the parity test fails otherwise.
- Models are as good as the simulated data they were trained on. New data (`make sim`) without re-running the notebooks leaves artifacts trained on older data; `metadata.json` records the data hash so this is visible.
- The deployed API and scoring Lambda must ship `models/` (packaging change, api handoff). The ETA `quantile_lgbm` strategy still fits on request; it lost to `median_by_cause` and was not exported.
- A weather forecast feed would cut load error most (notebook 03) but the scoring path has no weather input yet.
