"""Configuration settings for MCP Proxy Hub."""

import os
from typing import Set

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Server configuration
    host: str = Field(default="0.0.0.0", description="Host to bind the server to")
    port: int = Field(default=8000, description="Port to bind the server to")
    
    # Session configuration
    session_ttl_seconds: int = Field(
        default=1800,
        description="Session expiry time in seconds (30 minutes default)",
        alias="MCP_HUB_SESSION_TTL"
    )
    
    # Security configuration
    allowed_schemes: Set[str] = Field(
        default={"http", "https"},
        description="Allowed URL schemes for remote MCP servers"
    )
    
    denied_hosts: Set[str] = Field(
        default={"localhost", "127.0.0.1", "::1"},
        description="Denied hostnames/IPs to prevent SSRF attacks"
    )
    
    # Cleanup configuration
    cleanup_interval_seconds: int = Field(
        default=30,
        description="Interval between session cleanup runs in seconds"
    )
    
    # API configuration
    api_title: str = Field(default="MCP Hub API", description="API title")
    api_description: str = Field(
        default="Hub Server for Testing Remote MCP Servers via Dynamic Proxies",
        description="API description"
    )
    api_version: str = Field(default="0.1.0", description="API version")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="",
    )


# Global settings instance
settings = Settings()