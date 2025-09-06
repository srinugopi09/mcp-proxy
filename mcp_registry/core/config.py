"""
Configuration management using Pydantic Settings.

Centralized, type-safe configuration with environment variable support.
"""

from functools import lru_cache
from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "MCP Registry"
    app_version: str = "2.0.0"
    debug: bool = False
    
    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    api_workers: int = 1
    api_reload: bool = False
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./mcp_registry.db"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_echo: bool = False
    
    # Discovery
    discovery_timeout: int = 30
    discovery_cache_ttl: int = 3600
    discovery_max_concurrent: int = 10
    discovery_retry_attempts: int = 3
    
    # Security
    secret_key: str = Field(default="dev-secret-key-change-in-production")
    allowed_hosts: List[str] = Field(default_factory=lambda: ["*"])
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])
    
    # Monitoring & Logging
    log_level: str = "INFO"
    enable_metrics: bool = True
    metrics_port: int = 9090
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    
    # Proxy Settings
    proxy_timeout: int = 30
    proxy_max_connections: int = 100
    
    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'log_level must be one of {valid_levels}')
        return v.upper()
    
    @validator('database_url')
    def validate_database_url(cls, v):
        if not v.startswith(('sqlite', 'postgresql', 'mysql')):
            raise ValueError('database_url must start with sqlite, postgresql, or mysql')
        return v
    
    class Config:
        env_file = ".env"
        env_prefix = "MCP_"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()