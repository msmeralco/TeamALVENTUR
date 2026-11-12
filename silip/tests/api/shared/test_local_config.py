from pydantic_settings import SettingsConfigDict

from silip.shared.config import ApiSettings


def test_local_database_files_override_neon_without_changing_source(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_POOLER_URL", raising=False)
    monkeypatch.delenv("DATABASE_DIRECT_URL", raising=False)
    source = tmp_path / "env.dev"
    local = tmp_path / ".env.local"
    source_text = "DATABASE_POOLER_URL=postgresql://remote.example/neondb\nDATABASE_DIRECT_URL=postgresql://remote-direct.example/neondb\n"
    source.write_text(source_text)
    local.write_text(
        "DATABASE_URL=postgresql://127.0.0.1:55432/silip_local\nDATABASE_DIRECT_URL=postgresql://127.0.0.1:55432/silip_local\n"
    )

    class LocalSettings(ApiSettings):
        model_config = SettingsConfigDict(env_file=(source, local), extra="ignore")

    settings = LocalSettings()
    assert settings.database_url is not None
    assert settings.database_url.get_secret_value() == "postgresql://127.0.0.1:55432/silip_local"
    assert settings.database_direct_url is not None
    assert (
        settings.database_direct_url.get_secret_value()
        == "postgresql://127.0.0.1:55432/silip_local"
    )
    assert source.read_text() == source_text
