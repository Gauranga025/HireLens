import os
from unittest.mock import patch

from app.core.config import Settings, settings


def test_default_settings() -> None:
    """Test default configuration values."""
    assert settings.APP_NAME == "AI Resume Screening Backend"
    assert settings.APP_VERSION == "0.1.0"
    assert settings.DEBUG is False
    assert settings.API_PREFIX == "/api/v1"
    assert isinstance(settings.CORS_ORIGINS, list)
    assert len(settings.CORS_ORIGINS) > 0


def test_settings_from_env() -> None:
    """Test settings can be overridden by environment variables."""
    with patch.dict(os.environ, {
        "APP_NAME": "Test App",
        "APP_VERSION": "1.0.0",
        "DEBUG": "true",
    }):
        test_settings = Settings()
        assert test_settings.APP_NAME == "Test App"
        assert test_settings.APP_VERSION == "1.0.0"
        assert test_settings.DEBUG is True
