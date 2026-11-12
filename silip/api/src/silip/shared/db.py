"""Neon (Postgres) connections. `python -m silip.shared.db db/schema.sql` applies the schema."""

from __future__ import annotations

import sys
from pathlib import Path

import psycopg

from silip.shared.config import ApiSettings, ConfigError, get_settings

CONNECT_TIMEOUT_S = 10


def database_url(settings: ApiSettings) -> str:
    """DATABASE_URL from env (local) or Secrets Manager (Lambda). Never logged."""
    if settings.database_url is not None:
        return settings.database_url.get_secret_value()
    if settings.database_secret_arn:
        import boto3  # only needed in Lambda

        client = boto3.client("secretsmanager", region_name=settings.cognito_region)
        return client.get_secret_value(SecretId=settings.database_secret_arn)["SecretString"]
    raise ConfigError("Set DATABASE_URL (local) or DATABASE_SECRET_ARN (Lambda)")


def connect(settings: ApiSettings) -> psycopg.Connection:
    """Open a connection. Use the pooled Neon endpoint; Lambda opens many short connections."""
    return psycopg.connect(database_url(settings), connect_timeout=CONNECT_TIMEOUT_S)


def direct_url(settings: ApiSettings) -> str:
    """The unpooled endpoint for schema changes and bulk loads; falls back to DATABASE_URL."""
    direct = settings.database_direct_url
    return direct.get_secret_value() if direct is not None else database_url(settings)


def apply_schema(path: Path, settings: ApiSettings) -> None:
    """Run an additive SQL file (CREATE ... IF NOT EXISTS) over the direct, unpooled endpoint."""
    sql = path.read_text(encoding="utf-8")
    with psycopg.connect(direct_url(settings), connect_timeout=CONNECT_TIMEOUT_S) as connection:
        connection.execute(sql)  # type: ignore[arg-type]  # trusted file from the repo


if __name__ == "__main__":
    apply_schema(Path(sys.argv[1] if len(sys.argv) > 1 else "db/schema.sql"), get_settings())
    print("schema applied")
