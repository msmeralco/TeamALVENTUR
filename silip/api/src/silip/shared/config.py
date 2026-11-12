"""The only place the API reads environment variables. Extends the ml settings."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends
from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import SettingsConfigDict

from silip_ml.core.config import MlSettings

DataSourceName = Literal["simulated", "neon", "clamp", "smart_meter"]
WeatherSourceName = Literal["simulated", "open_meteo"]


class ConfigError(RuntimeError):
    """Raised when a required setting is missing or unsafe."""


class ApiSettings(MlSettings):
    """API settings. Strategy names (FORECASTER, RISK_SCORER, ...) come from MlSettings."""

    # Local overrides load last; shell variables take precedence. Missing files are skipped.
    model_config = SettingsConfigDict(
        env_file=(".env", "../env/env.dev", ".env.local"), extra="ignore"
    )

    data_source: DataSourceName = "simulated"
    # Pooled URL for the app (many short Lambda connections); direct URL for schema changes.
    database_url: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("DATABASE_URL", "DATABASE_POOLER_URL")
    )
    database_direct_url: SecretStr | None = None
    database_secret_arn: str | None = None
    auth_disabled: bool = False
    cognito_region: str = "ap-southeast-1"
    cognito_user_pool_id: str | None = None
    cognito_client_id: str | None = None
    # Hourly weather: simulated forecasts from data/sim, or Open-Meteo fetched server-side.
    weather_source: WeatherSourceName = "simulated"
    open_meteo_base_url: str = "https://api.open-meteo.com/v1/forecast"
    # Delivered (not simulated) inputs: data/evcs_locations.csv and data/ev_adoption.csv.
    ev_data_dir: Path = Path("data")

    @model_validator(mode="after")
    def _refuse_disabled_auth_in_lambda(self) -> ApiSettings:
        if self.auth_disabled and os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
            raise ConfigError("AUTH_DISABLED=true is for local dev and tests only, never in Lambda")
        return self


@lru_cache
def get_settings() -> ApiSettings:
    """Settings read once per process (overridden in tests)."""
    return ApiSettings()


Settings = Annotated[ApiSettings, Depends(get_settings)]
