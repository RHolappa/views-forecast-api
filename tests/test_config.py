import pytest

from app.core.config import Settings
from app.services.db_utils import sqlite_path_from_url


def test_cors_origins_parsed_from_json():
    settings = Settings(cors_origins='["https://example.com"]')
    assert settings.cors_origins == ["https://example.com"]


def test_normalize_data_backend_lowercases_value():
    settings = Settings(data_backend="CLOUD")
    assert settings.data_backend == "cloud"


def test_environment_validation():
    settings = Settings(environment="development")
    assert settings.is_development is True
    with pytest.raises(ValueError):
        Settings(environment="invalid")


def test_sqlite_path_from_url(tmp_path):
    db_path = tmp_path / "forecasts.db"
    url = f"sqlite:///{db_path}"
    resolved = sqlite_path_from_url(url)
    assert resolved == db_path


def test_sqlite_path_from_url_invalid_scheme():
    with pytest.raises(ValueError) as exc:
        sqlite_path_from_url("postgresql:///db")
    assert "Only sqlite URLs" in str(exc.value)
