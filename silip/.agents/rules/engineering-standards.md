# Engineering standards: KISS, DRY, SOLID, CLEAN

Apply to every language in the repo. When two rules conflict, prefer the simpler code (KISS) and leave a one-line comment on the trade-off.

## KISS
- Build the least code that meets today's requirement. No layers, flags or plugin systems "for later".
- Plain functions and frozen dataclasses before class hierarchies. A class only when it holds state or implements a port.
- Standard library and existing dependencies first. A new dependency needs a reason in the PR.

## DRY
- One source of truth per fact: schemas in `domain.py`, thresholds in one settings object, config in `config.py`.
- API and web types are generated from FastAPI's OpenAPI. The reading payload is exported as JSON Schema for the firmware. Never hand-copy a shape.
- Extract a helper on the second real duplicate, not the first.

## SOLID
- **S:** one reason to change per module (read, aggregate, score and store are separate).
- **O:** add behavior by adding a strategy or adapter, not by growing `if name == ...` chains.
- **L:** every implementation of a port passes the same contract test.
- **I:** small ports (`Forecaster.predict`, `DataSource.load`), not one big service.
- **D:** services depend on `Protocol` ports; adapters are injected in one composition root.

## Strategy pattern (how SILIP swaps parts)
Every swappable part is a `Protocol` plus implementations registered by name and chosen by config:
- `FORECASTER=seasonal_naive|lightgbm`
- `RISK_SCORER=rules|lightgbm`
- `OUTAGE_LOCATOR=nearest_report|dbscan`
- `ETA_ESTIMATOR=median_by_cause|quantile_lgbm`
- `DATA_SOURCE=simulated|clamp|smart_meter`

Each domain has one baseline. A strategy is kept only if the backtest shows it beats the baseline.

## CLEAN code
- Names say what, with units: `load_pct`, `eta_p50_min`, `rated_kva`. No `x2`, `tmp`, `do_step`.
- Small functions, one level of abstraction. No magic numbers; name them.
- Validate at the boundary (HTTP, MQTT, CSV load); trust data inside.
- Typed errors. Never swallow exceptions; never return `None` to mean "failed".
- Comments explain why. Delete commented-out code.

## Testing
- Domain and service: unit tests with in-memory fakes, no network.
- Adapters: contract test shared with the fake. Live-database tests are marked `integration` and skipped without `DATABASE_URL`.
- A bug fix starts with a failing test.

## Definition of done
1. `make lint test` passes (plus `make backtest` for model changes).
2. New behavior has a test.
3. The `reviewer` subagent found no blocking issue.
4. Docs or an ADR updated if a documented decision changed.
