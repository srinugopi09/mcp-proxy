"""Pytest configuration and shared fixtures."""

import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from mcp_proxy_hub.app import create_app
from mcp_proxy_hub.config import Settings
from mcp_proxy_hub.session import HubState


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings with safe defaults."""
    return Settings(
        host="127.0.0.1",
        port=8000,
        session_ttl_seconds=300,  # 5 minutes for tests
        cleanup_interval_seconds=10,  # Faster cleanup for tests
        denied_hosts={"localhost", "127.0.0.1", "::1", "test-denied.com"},
    )


@pytest.fixture
def mock_hub_state() -> HubState:
    """Create a mock hub state for testing."""
    hub_state = HubState()
    # Don't start the cleanup task in tests
    hub_state._cleanup_task = None
    return hub_state


@pytest.fixture
def app(test_settings: Settings, mock_hub_state: HubState):
    """Create a test FastAPI application."""
    # Patch the global settings and hub_state
    import mcp_proxy_hub.config
    import mcp_proxy_hub.session
    import mcp_proxy_hub.routes
    
    original_settings = mcp_proxy_hub.config.settings
    original_hub_state = mcp_proxy_hub.session.hub_state
    
    mcp_proxy_hub.config.settings = test_settings
    mcp_proxy_hub.session.hub_state = mock_hub_state
    mcp_proxy_hub.routes.hub_state = mock_hub_state
    
    app = create_app()
    
    yield app
    
    # Restore original instances
    mcp_proxy_hub.config.settings = original_settings
    mcp_proxy_hub.session.hub_state = original_hub_state
    mcp_proxy_hub.routes.hub_state = original_hub_state


@pytest.fixture
def client(app) -> TestClient:
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI application."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_proxy_client():
    """Create a mock proxy client for testing."""
    mock_client = AsyncMock()
    mock_client.new.return_value = mock_client
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.ping.return_value = None
    mock_client.list_tools.return_value = []
    mock_client.call_tool.return_value = MagicMock(
        content="test result",
        structured_content={"result": "test"}
    )
    return mock_client


@pytest.fixture
def mock_fastmcp():
    """Create a mock FastMCP instance for testing."""
    mock_fastmcp = MagicMock()
    mock_fastmcp.mount = MagicMock()
    mock_fastmcp.app = MagicMock()
    return mock_fastmcp


@pytest.fixture
def sample_session_request():
    """Sample session creation request data."""
    return {
        "remote_url": "https://example.com/mcp",
        "token": "test-token-123",
        "headers": {"X-Custom": "test-header"}
    }


@pytest.fixture
def sample_tool_call_request():
    """Sample tool call request data."""
    return {
        "arguments": {"param1": "value1", "param2": 42},
        "stream": False
    }