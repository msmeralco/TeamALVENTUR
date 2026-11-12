# ml (`silip_ml`)

Models, simulator and backtest. Importable by `api/` and `notebooks/`.

- Domains: `readings` (payload, simulate, aggregate), `load` (forecast), `risk` (score), `outages` (locate, ETA). Each has a `Protocol` in `domain.py` and one file per strategy.
- Pick a strategy by config (`FORECASTER=lightgbm`); `core/registry.py` maps names to classes.
- `make sim && make backtest` compares every configured strategy to its baseline on simulated data.
