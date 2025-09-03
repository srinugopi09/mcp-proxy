#!/usr/bin/env python3
"""
MCP Proxy Server

A standalone FastMCP server that acts as a proxy to any remote MCP server.
Given an MCP URL, it connects to the remote server and exposes all its
capabilities (tools, resources, prompts) through the proxy server.

Usage:
    python mcp_proxy_server.py <mcp_url> [--name <proxy_name>] [--port <port>] [--transport <transport>]

Examples:
    # Proxy an HTTP MCP server
    python mcp_proxy_server.py http://localhost:8000/mcp --name "MyProxy" --port 8001

    # Proxy an SSE MCP server  
    python mcp_proxy_server.py http://localhost:8000/sse --name "SSEProxy" --transport sse

    # Run via stdio (default)
    python mcp_proxy_server.py http://localhost:8000/mcp
"""

import argparse
import asyncio
import sys
from typing import Any

from fastmcp import FastMCP
from fastmcp.client import Client
from fastmcp.client.transports import SSETransport, StreamableHttpTransport, infer_transport
from fastmcp.server.proxy import FastMCPProxy
from fastmcp.utilities.logging import get_logger

logger = get_logger(__name__)


def create_client_factory(mcp_url: str, transport_type: str | None = None):
    """
    Creates a client factory function that returns a new Client instance
    configured to connect to the specified MCP URL.
    
    Args:
        mcp_url: The URL of the remote MCP server
        transport_type: Optional transport type override ('sse', 'http', or None for auto-detection)
    
    Returns:
        A callable that returns a Client instance
    """
    def client_factory() -> Client:
        if transport_type == "sse":
            transport = SSETransport(mcp_url)
        elif transport_type == "http":
            transport = StreamableHttpTransport(mcp_url)
        else:
            # Auto-detect transport based on URL
            transport = infer_transport(mcp_url)
        
        return Client(transport)
    
    return client_factory


async def create_proxy_server(
    mcp_url: str, 
    proxy_name: str = "MCPProxy",
    transport_type: str | None = None
) -> FastMCPProxy:
    """
    Creates a FastMCPProxy server that connects to the specified MCP URL.
    
    Args:
        mcp_url: The URL of the remote MCP server to proxy
        proxy_name: Name for the proxy server
        transport_type: Optional transport type override
    
    Returns:
        A configured FastMCPProxy instance
    """
    logger.info(f"Creating proxy server '{proxy_name}' for MCP URL: {mcp_url}")
    
    # Create client factory for the remote MCP server
    client_factory = create_client_factory(mcp_url, transport_type)
    
    # Test connection to ensure the remote server is accessible
    try:
        test_client = client_factory()
        async with test_client as client:
            # Try to initialize and get server info
            init_result = client.initialize_result
            server_info = init_result.serverInfo
            logger.info(f"Successfully connected to remote server: {server_info.name} v{server_info.version}")
    except Exception as e:
        logger.error(f"Failed to connect to remote MCP server at {mcp_url}: {e}")
        raise
    
    # Create the proxy server
    proxy_server = FastMCPProxy(
        client_factory=client_factory,
        name=proxy_name,
        version="1.0.0"
    )
    
    logger.info(f"Proxy server '{proxy_name}' created successfully")
    return proxy_server


async def run_proxy_server(
    mcp_url: str,
    proxy_name: str = "MCPProxy", 
    port: int | None = None,
    transport: str = "stdio",
    transport_type: str | None = None
):
    """
    Runs the MCP proxy server with the specified configuration.
    
    Args:
        mcp_url: The URL of the remote MCP server to proxy
        proxy_name: Name for the proxy server
        port: Port to run HTTP/SSE server on (ignored for stdio)
        transport: Transport type for the proxy server ('stdio', 'http', 'sse')
        transport_type: Transport type for connecting to remote server
    """
    # Create the proxy server
    proxy_server = await create_proxy_server(mcp_url, proxy_name, transport_type)
    
    # Run the server with the specified transport
    if transport == "stdio":
        logger.info(f"Starting proxy server '{proxy_name}' via stdio")
        await proxy_server.run_stdio()
    elif transport == "http":
        if port is None:
            port = 8000
        logger.info(f"Starting proxy server '{proxy_name}' via HTTP on port {port}")
        await proxy_server.run_http(port=port)
    elif transport == "sse":
        if port is None:
            port = 8000
        logger.info(f"Starting proxy server '{proxy_name}' via SSE on port {port}")
        await proxy_server.run_sse(port=port)
    else:
        raise ValueError(f"Unsupported transport type: {transport}")


def main():
    """Main entry point for the MCP proxy server."""
    parser = argparse.ArgumentParser(
        description="MCP Proxy Server - Proxy any remote MCP server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Proxy via stdio (default)
  python mcp_proxy_server.py http://localhost:8000/mcp
  
  # Proxy via HTTP on port 8001
  python mcp_proxy_server.py http://localhost:8000/mcp --transport http --port 8001
  
  # Proxy via SSE with custom name
  python mcp_proxy_server.py http://localhost:8000/sse --transport sse --name "MySSEProxy"
  
  # Force SSE transport for remote connection
  python mcp_proxy_server.py http://localhost:8000/mcp --transport-type sse
        """
    )
    
    parser.add_argument(
        "mcp_url",
        help="URL of the remote MCP server to proxy"
    )
    
    parser.add_argument(
        "--name",
        default="MCPProxy",
        help="Name for the proxy server (default: MCPProxy)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        help="Port to run the proxy server on (for HTTP/SSE transports)"
    )
    
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "sse"],
        default="stdio",
        help="Transport type for the proxy server (default: stdio)"
    )
    
    parser.add_argument(
        "--transport-type",
        choices=["sse", "http"],
        help="Force specific transport type for connecting to remote server (auto-detected if not specified)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.transport in ["http", "sse"] and args.port is None:
        print("Error: --port is required when using HTTP or SSE transport", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Run the proxy server
        asyncio.run(run_proxy_server(
            mcp_url=args.mcp_url,
            proxy_name=args.name,
            port=args.port,
            transport=args.transport,
            transport_type=args.transport_type
        ))
    except KeyboardInterrupt:
        logger.info("Proxy server stopped by user")
    except Exception as e:
        logger.error(f"Proxy server failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()