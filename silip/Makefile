# SILIP. Recipes avoid shell-specific syntax so they run from Git Bash, PowerShell or cmd.
.PHONY: setup sim notebooks test lint fmt backtest api web schemas db tf-validate iot-test

setup:
	uv sync
	cd web && npm ci

# Mock data comes from notebooks/00 only. SIM_SCALE=test|dev|large|xlarge (make sim SIM_SCALE=test).
SIM_SCALE ?= dev
export SIM_SCALE
NBCONVERT = uv run --group notebooks jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=1800

sim:
	$(NBCONVERT) --output-dir data/sim --output 00_generate_mock_data.executed notebooks/00_generate_mock_data.ipynb

# Re-run every notebook in order and keep outputs (training, evaluation, export to models/).
notebooks:
	$(NBCONVERT) --inplace notebooks/00_generate_mock_data.ipynb notebooks/01_data_overview.ipynb notebooks/02_eda.ipynb notebooks/03_features_and_preprocessing.ipynb notebooks/04_train_load_forecast.ipynb notebooks/05_train_risk_model.ipynb notebooks/06_evaluate_and_export.ipynb

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
