# Python rules (`ml/`, `api/`)

On top of [engineering-standards.md](engineering-standards.md).

## Toolchain
- Python 3.12, **uv** workspace at the repo root (`uv sync`, `uv run`, `uv add`). Never `pip install` into the project.
- **ruff** (format + lint), **pyright** (standard), **pytest**, **import-linter**. Config in the root `pyproject.toml`.

## Packages
- `ml/src/silip_ml/`: inference only (load an exported model, build its features from live data, predict in one batch) plus the backtest. Importable by `api/`. Never imports `silip` (the API) and never trains.
- `notebooks/`: everything before inference: mock data, EDA, preprocessing, features, training, tuning, evaluation, export. Self-contained: notebooks never import `silip_ml`; shared notebook code lives in small `notebooks/_*.py` modules.
- `models/<task>/<name>/`: exported artifacts (LightGBM text `model.txt`, never pickle; `metadata.json` with features, parameters, training window, data seed, metrics, versions) and a `parity/` sample. Inference reads features and parameters from `metadata.json`, never from a hardcoded copy.
- `api/src/silip/`: FastAPI app; Lambda handler via Mangum.

## Layers inside every API feature
`api.py` → `adapters.py` → `service.py` → `domain.py`. Imports point down only (import-linter).

| module | holds | may import |
|---|---|---|
| `domain.py` | frozen dataclasses or Pydantic models, enums, `Protocol` ports, pure rules | stdlib, `silip.shared`, `silip_ml` |
| `service.py` | use cases taking ports as arguments | `domain`, `shared`, `silip_ml` |
| `adapters.py` | port implementations (Neon, CSV, Cognito JWKS) | `service`, `domain`, `shared`, third-party |
| `api.py` | FastAPI router | all of the above |

- Features never import another feature's `adapters`. `shared/` imports no feature.
- Wiring (which adapter, which strategy) happens only in FastAPI dependencies.

## ml/ layout
`silip_ml/<domain>/domain.py` holds the port. Each strategy is one file registered with `@register("<task>", "<name>")`; trained strategies load their artifact (`silip_ml/core/artifacts.py`). `silip_ml/features.py` rebuilds the notebook features for inference, for every transformer at once. `metrics.py` holds the backtest metric. `silip_ml/core/` holds config, registry, artifacts and privacy; `silip_ml/backtest.py` compares exported models with baselines and refuses one trained on held-out days.

## Train/serve parity
Features are written twice: `notebooks/_features.py` (training) and `silip_ml/features.py` (inference). The export notebook writes input rows, features and expected predictions to `models/<task>/<name>/parity/`; `tests/ml/test_parity.py` must reproduce them bit for bit. Change a feature in both places, re-run notebooks 04 to 06, and commit the new artifacts and parity sample together.

## Style
- Type hints on every public function. No `Any` without a comment saying why.
- Data crossing a boundary (HTTP, MQTT, CSV) is a Pydantic model.
- Env vars are read only in `config.py` (pydantic-settings).
- No module-level side effects (no clients at import). No `print` outside CLIs; use `logging`.
- Timeouts on every network call.
