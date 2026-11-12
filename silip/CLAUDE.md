# SILIP

Estimates each Meralco transformer's load and risk by summing opt-in household clamp readings by Service ID Number (SIN). Flags overloads, EV load and outages for engineers. Outputs: engineer risk map, outage view, household usage view. Spec: `docs/SPEC.md`.

## Commands (repo root)
- `make setup` (uv sync + npm ci) · `make sim` · `make test` · `make lint` · `make backtest` · `make api` · `make web` · `make schemas`
- One backtest: `uv run python -m silip_ml.backtest --domain risk --strategy lightgbm` (domains: load, risk, locate, eta)
- Infra: `make tf-validate`; deploy only via `/deploy`. Schema: `make db` (Neon URLs from `../env/env.dev`). Firmware: `make iot-test` (needs PlatformIO)

## How to work
- State assumptions before coding. Ask only if a wrong guess is expensive.
- Write the least code that meets the goal. No speculative abstractions.
- Change only what the task needs.
- Finish with a check you actually ran (test, backtest number, screenshot). Report its output.

## Hard rules
- SINs only as salted hashes (`sin_hash`). Never raw SINs in code, data, logs or fixtures.
- Simulated data is labeled `is_simulated` everywhere, including UI and reports.
- Nothing in this project touches Meralco's meter, seal, service drop or transformer.
- No invented numbers in docs or UI. Cite `docs/SPEC.md#sources` or mark `[VERIFY]`.

## Where knowledge lives (load only when needed)
- Engineering rules → `AGENTS.md` and `.agents/rules/`
- Formulas, simulation, metrics → skill `silip-domain`
- Data folders, MQTT, Neon schema → skill `data-access`
- Backtests and report table → skill `run-backtest`
- UI and copy → skill `unslop`
- Auth → `docs/auth-contract.md`
- Decisions → skill `write-adr`; deploy → `/deploy`
