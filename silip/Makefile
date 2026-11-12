# SILIP. Recipes avoid shell-specific syntax so they run from Git Bash, PowerShell or cmd.
.PHONY: setup sim test lint fmt backtest api web schemas db tf-validate iot-test

setup:
	uv sync
	cd web && npm ci

sim:
	uv run python -m silip_ml.readings.simulate --transformers 50 --days 30 --out data/sim

test:
	uv run pytest
	cd web && npm test

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run pyright
	uv run lint-imports
	cd web && npm run lint
	terraform fmt -check -recursive infra

fmt:
	uv run ruff check --fix .
	uv run ruff format .
	cd web && npx prettier --write "src/**/*.{ts,tsx,css}"
	terraform fmt -recursive infra

backtest:
	uv run python -m silip_ml.backtest

api:
	uv run uvicorn silip.app:app --reload --port 8000

web:
	cd web && npm run dev

schemas:
	uv run python -m silip_ml.readings.domain schemas/reading.json
	uv run python -m silip.app web/openapi.json
	cd web && npm run gen:api

db:
	uv run python -m silip.shared.db db/schema.sql

tf-validate:
	terraform -chdir=infra/envs/dev init -backend=false -input=false
	terraform -chdir=infra/envs/dev validate
	terraform -chdir=infra/envs/prod init -backend=false -input=false
	terraform -chdir=infra/envs/prod validate

iot-test:
	cd iot && pio test -e native
