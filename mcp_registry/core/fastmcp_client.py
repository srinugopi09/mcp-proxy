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
    """Convert MCP capabilities to our internal capability format."""
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
            "schema": getattr(tool, 'inputSchema', {}),  # MCP uses camelCase
            "metadata": {
                "discovered_at": datetime.now(UTC).isoformat(),
                "discovery_method": "fastmcp",
                "tool_type": "mcp_tool",
                "output_schema": getattr(tool, 'outputSchema', None)
            }
        })
    
    # Convert resources
    for resource in resources:
        capabilities.append({
            "id": str(uuid.uuid4()),
            "server_id": server_id,
            "name": getattr(resource, 'name', str(resource.uri)),  # Resources may not have name
            "type": "resource",
            "description": resource.description or "",
            "schema": {
                "uri": str(resource.uri),  # Convert AnyUrl to string
                "mime_type": getattr(resource, 'mimeType', None)  # MCP uses camelCase
            },
            "metadata": {
                "discovered_at": datetime.now(UTC).isoformat(),
                "discovery_method": "fastmcp",
                "resource_uri": str(resource.uri),
                "mime_type": getattr(resource, 'mimeType', None),
                "size": getattr(resource, 'size', None)
            }
        })
    
    # Convert prompts
    for prompt in prompts:
        # Extract argument details if available
        arguments = []
        if hasattr(prompt, 'arguments') and prompt.arguments:
            for arg in prompt.arguments:
                arguments.append({
                    "name": arg.name,
                    "description": getattr(arg, 'description', None),
                    "required": getattr(arg, 'required', None)
                })
        
        capabilities.append({
            "id": str(uuid.uuid4()),
            "server_id": server_id,
            "name": prompt.name,
            "type": "prompt",
            "description": prompt.description or "",
            "schema": {
                "arguments": arguments
            },
            "metadata": {
                "discovered_at": datetime.now(UTC).isoformat(),
                "discovery_method": "fastmcp",
                "prompt_arguments": arguments
            }
        })
    
    return capabilities