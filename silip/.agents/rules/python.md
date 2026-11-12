# Python rules (`ml/`, `api/`)

On top of [engineering-standards.md](engineering-standards.md).

## Toolchain
- Python 3.12, **uv** workspace at the repo root (`uv sync`, `uv run`, `uv add`). Never `pip install` into the project.
- **ruff** (format + lint), **pyright** (standard), **pytest**, **import-linter**. Config in the root `pyproject.toml`.

## Packages
- `ml/src/silip_ml/`: models and data logic, importable by `api/` and `notebooks/`. Never imports `silip` (the API).
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
`silip_ml/<domain>/domain.py` holds the port. Each strategy is one file registered with `@register("<task>", "<name>")`. `metrics.py` holds the backtest metric. `silip_ml/core/` holds config, registry, privacy and backtest.

## Style
- Type hints on every public function. No `Any` without a comment saying why.
- Data crossing a boundary (HTTP, MQTT, CSV) is a Pydantic model.
- Env vars are read only in `config.py` (pydantic-settings).
- No module-level side effects (no clients at import). No `print` outside CLIs; use `logging`.
- Timeouts on every network call.
