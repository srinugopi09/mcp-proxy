"""Unit tests for configuration module."""

import os
from unittest.mock import patch

import pytest

from mcp_proxy_hub.config import Settings


class TestSettings:
    """Test the Settings class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        settings = Settings()
        
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.session_ttl_seconds == 1800
        assert settings.allowed_schemes == {"http", "https"}
        assert "localhost" in settings.denied_hosts
        assert "127.0.0.1" in settings.denied_hosts
        assert "::1" in settings.denied_hosts

    def test_environment_variable_override(self):
        """Test that environment variables override defaults."""
        with patch.dict(os.environ, {"MCP_HUB_SESSION_TTL": "3600"}):
            settings = Settings()
            assert settings.session_ttl_seconds == 3600

    def test_custom_values(self):
        """Test setting custom values."""
        settings = Settings(
            host="127.0.0.1",
            port=9000,
            session_ttl_seconds=7200,
        )
        
        assert settings.host == "127.0.0.1"
        assert settings.port == 9000
        assert settings.session_ttl_seconds == 7200

    def test_api_configuration(self):
        """Test API-related configuration."""
        settings = Settings()
        
        assert settings.api_title == "MCP Hub API"
        assert "Hub Server" in settings.api_description
        assert settings.api_version == "0.1.0"

    def test_cleanup_configuration(self):
        """Test cleanup-related configuration."""
        settings = Settings()
        
        assert settings.cleanup_interval_seconds == 30