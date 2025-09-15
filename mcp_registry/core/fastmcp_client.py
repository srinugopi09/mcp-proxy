"""
FastMCP client utilities for MCP Registry.

This module provides utilities for creating FastMCP clients using the proper
context manager pattern. No caching is used - fresh clients are created for
each operation as per FastMCP best practices.
"""

from typing import Any
from datetime import datetime, UTC

from fastmcp.client import Client, SSETransport, StreamableHttpTransport


def create_transport(server_url: str, transport_type: str = "auto"):
    """Create appropriate transport for the server URL."""
    if transport_type == "sse" or (transport_type == "auto" and "/mcp" in server_url):
        return SSETransport(server_url)
    elif transport_type == "http" or transport_type == "auto":
        return StreamableHttpTransport(server_url)
    else:
        # Default to SSE for MCP endpoints
        return SSETransport(server_url)


def create_fastmcp_client(server_url: str, transport_type: str = "auto") -> Client:
    """Create a new FastMCP client for the given server.
    
    Note: The client must be used with 'async with client:' context manager.
    """
    transport = create_transport(server_url, transport_type)
    return Client(transport)


def convert_mcp_capabilities_to_dict(tools, resources, prompts, server_id: str) -> list:
    """Convert FastMCP capabilities to our internal capability format."""
    import uuid
    
    capabilities = []
    
    # Convert tools
    for tool in tools:
        capabilities.append({
            "id": str(uuid.uuid4()),
            "server_id": server_id,
            "name": tool.name,
            "type": "tool",
            "description": tool.description or "",
            "schema": tool.input_schema or {},
            "metadata": {
                "discovered_at": datetime.now(UTC).isoformat(),
                "discovery_method": "fastmcp",
                "tool_type": "mcp_tool"
            }
        })
    
    # Convert resources
    for resource in resources:
        capabilities.append({
            "id": str(uuid.uuid4()),
            "server_id": server_id,
            "name": resource.name or resource.uri,
            "type": "resource",
            "description": resource.description or "",
            "schema": {
                "uri": resource.uri,
                "mime_type": getattr(resource, 'mime_type', None)
            },
            "metadata": {
                "discovered_at": datetime.now(UTC).isoformat(),
                "discovery_method": "fastmcp",
                "resource_uri": resource.uri,
                "mime_type": getattr(resource, 'mime_type', None)
            }
        })
    
    # Convert prompts
    for prompt in prompts:
        capabilities.append({
            "id": str(uuid.uuid4()),
            "server_id": server_id,
            "name": prompt.name,
            "type": "prompt",
            "description": prompt.description or "",
            "schema": {
                "arguments": getattr(prompt, 'arguments', [])
            },
            "metadata": {
                "discovered_at": datetime.now(UTC).isoformat(),
                "discovery_method": "fastmcp",
                "prompt_arguments": getattr(prompt, 'arguments', [])
            }
        })
    
    return capabilities