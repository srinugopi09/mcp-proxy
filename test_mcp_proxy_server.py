#!/usr/bin/env python3
"""
Tests for the MCP Proxy Server

This test suite validates that the proxy server correctly forwards
all MCP capabilities from remote servers.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from mcp.types import TextContent, Tool as MCPTool, Resource as MCPResource, Prompt as MCPPrompt

from fastmcp import FastMCP
from fastmcp.client import Client
from fastmcp.server.proxy import FastMCPProxy
from mcp_proxy_server import create_client_factory, create_proxy_server


class TestMCPProxyServer:
    """Test suite for MCP Proxy Server functionality."""

    async def test_create_client_factory(self):
        """Test that client factory creates proper client instances."""
        mcp_url = "http://localhost:8000/mcp"
        
        # Test auto-detection (should create StreamableHttpTransport)
        factory = create_client_factory(mcp_url)
        client = factory()
        assert isinstance(client, Client)
        
        # Test explicit SSE transport
        factory_sse = create_client_factory(mcp_url, "sse")
        client_sse = factory_sse()
        assert isinstance(client_sse, Client)
        
        # Test explicit HTTP transport
        factory_http = create_client_factory(mcp_url, "http")
        client_http = factory_http()
        assert isinstance(client_http, Client)

    async def test_proxy_server_creation_with_mock_server(self):
        """Test proxy server creation with a mock remote server."""
        # Create a mock original server
        original_server = FastMCP("TestOriginalServer")
        
        @original_server.tool
        def test_tool(message: str) -> str:
            """A test tool that echoes a message."""
            return f"Echo: {message}"
        
        @original_server.resource("test://resource")
        def test_resource() -> str:
            """A test resource."""
            return "Test resource content"
        
        @original_server.prompt
        def test_prompt(name: str) -> str:
            """A test prompt."""
            return f"Hello, {name}!"
        
        # Create proxy using the original server directly (in-memory)
        proxy_server = FastMCPProxy(
            client_factory=lambda: Client(original_server),
            name="TestProxy"
        )
        
        # Test that proxy server was created
        assert proxy_server.name == "TestProxy"
        assert isinstance(proxy_server, FastMCPProxy)
        
        # Test proxy functionality
        async with Client(proxy_server) as proxy_client:
            # Test tools
            tools = await proxy_client.list_tools()
            assert len(tools) == 1
            assert tools[0].name == "test_tool"
            
            tool_result = await proxy_client.call_tool("test_tool", {"message": "Hello"})
            assert isinstance(tool_result[0], TextContent)
            assert tool_result[0].text == "Echo: Hello"
            
            # Test resources
            resources = await proxy_client.list_resources()
            assert len(resources) == 1
            assert str(resources[0].uri) == "test://resource"
            
            resource_content = await proxy_client.read_resource("test://resource")
            assert isinstance(resource_content[0], TextContent)
            assert resource_content[0].text == "Test resource content"
            
            # Test prompts
            prompts = await proxy_client.list_prompts()
            assert len(prompts) == 1
            assert prompts[0].name == "test_prompt"
            
            prompt_result = await proxy_client.get_prompt("test_prompt", {"name": "World"})
            assert len(prompt_result.messages) == 1
            assert "Hello, World!" in prompt_result.messages[0].content.text

    async def test_proxy_server_with_empty_remote_server(self):
        """Test proxy server behavior with an empty remote server."""
        # Create an empty server
        empty_server = FastMCP("EmptyServer")
        
        # Create proxy
        proxy_server = FastMCPProxy(
            client_factory=lambda: Client(empty_server),
            name="EmptyProxy"
        )
        
        # Test that proxy handles empty server gracefully
        async with Client(proxy_server) as proxy_client:
            tools = await proxy_client.list_tools()
            assert len(tools) == 0
            
            resources = await proxy_client.list_resources()
            assert len(resources) == 0
            
            prompts = await proxy_client.list_prompts()
            assert len(prompts) == 0

    async def test_proxy_server_error_handling(self):
        """Test proxy server error handling for invalid tool calls."""
        # Create a server with a tool
        original_server = FastMCP("ErrorTestServer")
        
        @original_server.tool
        def error_tool(should_error: bool) -> str:
            """A tool that can throw errors."""
            if should_error:
                raise ValueError("Test error")
            return "Success"
        
        # Create proxy
        proxy_server = FastMCPProxy(
            client_factory=lambda: Client(original_server),
            name="ErrorProxy"
        )
        
        async with Client(proxy_server) as proxy_client:
            # Test successful call
            result = await proxy_client.call_tool("error_tool", {"should_error": False})
            assert isinstance(result[0], TextContent)
            assert result[0].text == "Success"
            
            # Test error call
            with pytest.raises(Exception):
                await proxy_client.call_tool("error_tool", {"should_error": True})

    async def test_proxy_server_multiple_tools(self):
        """Test proxy server with multiple tools of different types."""
        original_server = FastMCP("MultiToolServer")
        
        @original_server.tool
        def string_tool(text: str) -> str:
            """Returns a string."""
            return f"String: {text}"
        
        @original_server.tool
        def number_tool(num: int) -> int:
            """Returns a number."""
            return num * 2
        
        @original_server.tool
        def complex_tool(data: dict) -> dict:
            """Returns complex data."""
            return {"processed": data, "status": "complete"}
        
        # Create proxy
        proxy_server = FastMCPProxy(
            client_factory=lambda: Client(original_server),
            name="MultiToolProxy"
        )
        
        async with Client(proxy_server) as proxy_client:
            tools = await proxy_client.list_tools()
            assert len(tools) == 3
            
            tool_names = {tool.name for tool in tools}
            assert tool_names == {"string_tool", "number_tool", "complex_tool"}
            
            # Test each tool
            result1 = await proxy_client.call_tool("string_tool", {"text": "test"})
            assert isinstance(result1[0], TextContent)
            assert result1[0].text == "String: test"
            
            result2 = await proxy_client.call_tool("number_tool", {"num": 5})
            assert isinstance(result2[0], TextContent)
            assert result2[0].text == "10"
            
            result3 = await proxy_client.call_tool("complex_tool", {"data": {"key": "value"}})
            assert isinstance(result3[0], TextContent)
            # The result should be JSON-serialized
            import json
            parsed = json.loads(result3[0].text)
            assert parsed["processed"]["key"] == "value"
            assert parsed["status"] == "complete"


async def run_tests():
    """Run all tests."""
    test_instance = TestMCPProxyServer()
    
    print("Running MCP Proxy Server tests...")
    
    try:
        await test_instance.test_create_client_factory()
        print("✅ test_create_client_factory passed")
        
        await test_instance.test_proxy_server_creation_with_mock_server()
        print("✅ test_proxy_server_creation_with_mock_server passed")
        
        await test_instance.test_proxy_server_with_empty_remote_server()
        print("✅ test_proxy_server_with_empty_remote_server passed")
        
        await test_instance.test_proxy_server_error_handling()
        print("✅ test_proxy_server_error_handling passed")
        
        await test_instance.test_proxy_server_multiple_tools()
        print("✅ test_proxy_server_multiple_tools passed")
        
        print("\n🎉 All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_tests())