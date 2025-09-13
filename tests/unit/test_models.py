"""Unit tests for models module."""

from datetime import datetime
from typing import Any, Dict

import pytest
from pydantic import ValidationError

from mcp_proxy_hub.models import (
    CreateSessionRequest,
    CreateSessionResponse,
    ToolCallRequest,
    ToolCallResponse,
    ToolInfo,
    ToolsListResponse,
)


class TestCreateSessionRequest:
    """Test the CreateSessionRequest model."""

    def test_valid_request(self):
        """Test creating a valid session request."""
        data = {
            "remote_url": "https://example.com/mcp",
            "token": "test-token",
            "headers": {"X-Custom": "value"}
        }
        request = CreateSessionRequest(**data)
        
        assert str(request.remote_url) == "https://example.com/mcp"
        assert request.token == "test-token"
        assert request.headers == {"X-Custom": "value"}

    def test_minimal_request(self):
        """Test creating a request with only required fields."""
        data = {"remote_url": "https://example.com/mcp"}
        request = CreateSessionRequest(**data)
        
        assert str(request.remote_url) == "https://example.com/mcp"
        assert request.token is None
        assert request.headers is None

    def test_invalid_url(self):
        """Test that invalid URLs are rejected."""
        data = {"remote_url": "not-a-url"}
        
        with pytest.raises(ValidationError):
            CreateSessionRequest(**data)

    def test_url_validation(self):
        """Test URL validation."""
        # Valid URLs
        valid_urls = [
            "https://example.com/mcp",
            "http://api.example.com:8080/mcp",
            "https://subdomain.example.com/api/v1/mcp"
        ]
        
        for url in valid_urls:
            request = CreateSessionRequest(remote_url=url)
            assert str(request.remote_url) == url


class TestCreateSessionResponse:
    """Test the CreateSessionResponse model."""

    def test_valid_response(self):
        """Test creating a valid session response."""
        expires_at = datetime.utcnow()
        data = {
            "session_id": "abc123",
            "prefix": "abc123",
            "remote_url": "https://example.com/mcp",
            "expires_at": expires_at
        }
        response = CreateSessionResponse(**data)
        
        assert response.session_id == "abc123"
        assert response.prefix == "abc123"
        assert str(response.remote_url) == "https://example.com/mcp"
        assert response.expires_at == expires_at


class TestToolCallRequest:
    """Test the ToolCallRequest model."""

    def test_valid_request(self):
        """Test creating a valid tool call request."""
        data = {
            "arguments": {"param1": "value1", "param2": 42},
            "stream": True
        }
        request = ToolCallRequest(**data)
        
        assert request.arguments == {"param1": "value1", "param2": 42}
        assert request.stream is True

    def test_minimal_request(self):
        """Test creating a request with only required fields."""
        data = {"arguments": {}}
        request = ToolCallRequest(**data)
        
        assert request.arguments == {}
        assert request.stream is False  # Default value

    def test_complex_arguments(self):
        """Test with complex argument structures."""
        complex_args = {
            "simple": "string",
            "number": 123,
            "boolean": True,
            "list": [1, 2, 3],
            "nested": {"key": "value", "count": 5}
        }
        request = ToolCallRequest(arguments=complex_args)
        
        assert request.arguments == complex_args


class TestToolCallResponse:
    """Test the ToolCallResponse model."""

    def test_valid_response(self):
        """Test creating a valid tool call response."""
        data = {
            "content": "Tool executed successfully",
            "structured_content": {"result": "success", "data": [1, 2, 3]}
        }
        response = ToolCallResponse(**data)
        
        assert response.content == "Tool executed successfully"
        assert response.structured_content == {"result": "success", "data": [1, 2, 3]}

    def test_empty_response(self):
        """Test creating an empty response."""
        response = ToolCallResponse()
        
        assert response.content is None
        assert response.structured_content is None


class TestToolInfo:
    """Test the ToolInfo model."""

    def test_valid_tool_info(self):
        """Test creating valid tool info."""
        data = {
            "name": "example-tool",
            "description": "An example tool",
            "arguments": {"param1": {"type": "string"}},
            "returns": {"type": "object"},
            "structured": True
        }
        tool_info = ToolInfo(**data)
        
        assert tool_info.name == "example-tool"
        assert tool_info.description == "An example tool"
        assert tool_info.arguments == {"param1": {"type": "string"}}
        assert tool_info.returns == {"type": "object"}
        assert tool_info.structured is True

    def test_minimal_tool_info(self):
        """Test creating tool info with only required fields."""
        data = {"name": "simple-tool"}
        tool_info = ToolInfo(**data)
        
        assert tool_info.name == "simple-tool"
        assert tool_info.description is None
        assert tool_info.arguments is None
        assert tool_info.returns is None
        assert tool_info.structured is False  # Default value


class TestToolsListResponse:
    """Test the ToolsListResponse model."""

    def test_valid_tools_list(self):
        """Test creating a valid tools list response."""
        tools = [
            ToolInfo(name="tool1", description="First tool"),
            ToolInfo(name="tool2", description="Second tool", structured=True)
        ]
        data = {
            "tools": tools,
            "session_id": "abc123"
        }
        response = ToolsListResponse(**data)
        
        assert len(response.tools) == 2
        assert response.tools[0].name == "tool1"
        assert response.tools[1].name == "tool2"
        assert response.tools[1].structured is True
        assert response.session_id == "abc123"

    def test_empty_tools_list(self):
        """Test creating an empty tools list."""
        data = {
            "tools": [],
            "session_id": "abc123"
        }
        response = ToolsListResponse(**data)
        
        assert response.tools == []
        assert response.session_id == "abc123"