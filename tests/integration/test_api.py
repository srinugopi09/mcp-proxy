"""Integration tests for API endpoints."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestSessionEndpoints:
    """Test session management endpoints."""

    @patch("mcp_proxy_hub.session.StreamableHttpTransport")
    @patch("mcp_proxy_hub.session.ProxyClient")
    @patch("mcp_proxy_hub.session.FastMCP.as_proxy")
    def test_create_session_success(
        self, mock_as_proxy, mock_proxy_client, mock_transport, client: TestClient
    ):
        """Test successful session creation."""
        # Setup mocks
        mock_proxy_server = MagicMock()
        mock_as_proxy.return_value = mock_proxy_server
        mock_client_instance = MagicMock()
        mock_proxy_client.return_value = mock_client_instance

        # Make request
        response = client.post(
            "/session",
            json={
                "remote_url": "https://example.com/mcp",
                "token": "test-token"
            }
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "prefix" in data
        assert data["remote_url"] == "https://example.com/mcp"
        assert "expires_at" in data

        # Verify mocks were called
        mock_transport.assert_called_once()
        mock_proxy_client.assert_called_once()
        mock_as_proxy.assert_called_once()

    def test_create_session_invalid_url(self, client: TestClient):
        """Test session creation with invalid URL."""
        response = client.post(
            "/session",
            json={"remote_url": "ftp://example.com/mcp"}
        )

        assert response.status_code == 400
        assert "HTTP/HTTPS" in response.json()["detail"]

    def test_create_session_denied_host(self, client: TestClient):
        """Test session creation with denied host."""
        response = client.post(
            "/session",
            json={"remote_url": "http://localhost/mcp"}
        )

        assert response.status_code == 400
        assert "local/private hosts" in response.json()["detail"]

    def test_close_session_not_found(self, client: TestClient):
        """Test closing a non-existent session."""
        response = client.delete("/session/nonexistent")

        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]

    def test_refresh_session_not_found(self, client: TestClient):
        """Test refreshing a non-existent session."""
        response = client.post("/session/nonexistent/refresh")

        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]


class TestToolEndpoints:
    """Test tool-related endpoints."""

    def test_list_tools_session_not_found(self, client: TestClient):
        """Test listing tools for non-existent session."""
        response = client.get("/session/nonexistent/tools")

        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]

    def test_call_tool_session_not_found(self, client: TestClient):
        """Test calling tool for non-existent session."""
        response = client.post(
            "/session/nonexistent/tools/test-tool",
            json={"arguments": {}}
        )

        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]

    @patch("mcp_proxy_hub.routes.hub_state")
    def test_list_tools_success(self, mock_hub_state, client: TestClient):
        """Test successful tool listing."""
        # Setup mock session
        mock_session = MagicMock()
        mock_client = AsyncMock()
        mock_session.proxy_client = mock_client
        mock_client.new.return_value = mock_client
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        # Setup mock tools
        mock_tool = MagicMock()
        mock_tool.name = "test-tool"
        mock_tool.description = "A test tool"
        mock_tool.arguments = {"param": {"type": "string"}}
        mock_tool.returns = {"type": "object"}
        mock_tool.structured = True
        mock_client.list_tools.return_value = [mock_tool]

        mock_hub_state.get_session.return_value = mock_session

        # Make request
        response = client.get("/session/test-session/tools")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert len(data["tools"]) == 1
        assert data["tools"][0]["name"] == "test-tool"
        assert data["tools"][0]["description"] == "A test tool"
        assert data["tools"][0]["structured"] is True

    @patch("mcp_proxy_hub.routes.hub_state")
    def test_call_tool_success(self, mock_hub_state, client: TestClient):
        """Test successful tool call."""
        # Setup mock session
        mock_session = MagicMock()
        mock_client = AsyncMock()
        mock_session.proxy_client = mock_client
        mock_client.new.return_value = mock_client
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        # Setup mock tool result
        mock_result = MagicMock()
        mock_result.content = "Tool result"
        mock_result.structured_content = {"result": "success"}
        mock_client.call_tool.return_value = mock_result

        mock_hub_state.get_session.return_value = mock_session

        # Make request
        response = client.post(
            "/session/test-session/tools/test-tool",
            json={
                "arguments": {"param": "value"},
                "stream": False
            }
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Tool result"
        assert data["structured_content"] == {"result": "success"}

    @patch("mcp_proxy_hub.routes.hub_state")
    def test_ping_success(self, mock_hub_state, client: TestClient):
        """Test successful ping."""
        # Setup mock session
        mock_session = MagicMock()
        mock_client = AsyncMock()
        mock_session.proxy_client = mock_client
        mock_client.new.return_value = mock_client
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.ping.return_value = None

        mock_hub_state.get_session.return_value = mock_session

        # Make request
        response = client.get("/session/test-session/ping")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["detail"] == "pong"
        assert data["session_id"] == "test-session"


class TestApplicationSetup:
    """Test application setup and configuration."""

    def test_app_creation(self, client: TestClient):
        """Test that the application is created correctly."""
        # Test that the app responds to requests
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_spec(self, client: TestClient):
        """Test that OpenAPI spec is available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        spec = response.json()
        assert spec["info"]["title"] == "MCP Hub API"
        assert "paths" in spec
        assert "/session" in spec["paths"]