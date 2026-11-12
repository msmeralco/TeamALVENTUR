"""The only place ml/ reads environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Simulator-only default; deployed environments set SILIP_SIN_SALT from Secrets Manager.
DEV_SIN_SALT = "dev-salt-change-me"


class MlSettings(BaseSettings):
    """Strategy choice per task and where the data lives. Example: FORECASTER=lightgbm."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_dir: Path = Path("data/sim")
    models_dir: Path = Path("models")  # exported by notebooks/06_evaluate_and_export.ipynb
    sin_salt: str = Field(
        default=DEV_SIN_SALT, validation_alias=AliasChoices("SILIP_SIN_SALT", "SIN_SALT")
    )
    forecaster: str = "seasonal_naive"
    risk_scorer: str = "rules"
    outage_locator: str = "nearest_report"
    eta_estimator: str = "median_by_cause"


@lru_cache
def get_ml_settings() -> MlSettings:
    """Settings read once per process."""
    return MlSettings()
