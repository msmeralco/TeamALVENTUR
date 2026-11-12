# ml (`silip_ml`)

Inference and the backtest. Importable by `api/`. Training lives in `notebooks/`; this package never trains.

- Domains: `readings` (payload, aggregate, dataset loading), `load` (forecast), `risk` (score), `outages` (locate, ETA). Each has a `Protocol` in `domain.py` and one file per strategy.
- Trained strategies (`load/lightgbm.py`, `risk/lightgbm.py`) load `models/<task>/<name>/` (`core/artifacts.py`) and predict every transformer in one call. `features.py` rebuilds the notebook features from `metadata.json`; `tests/ml/test_parity.py` checks it against the exported parity sample.
- Pick a strategy by config (`FORECASTER=lightgbm`); `core/registry.py` maps names to classes. `MODELS_DIR` (default `models`) says where artifacts live.
- `make backtest` compares each exported model with its baseline on the held-out week of `data/sim`.
