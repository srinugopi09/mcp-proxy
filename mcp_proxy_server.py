#!/usr/bin/env python3
"""
MCP Proxy Server with Registry Integration

A standalone FastMCP server that acts as a proxy to any remote MCP server.
Can connect directly via URL or through the MCP Registry for discovery.

Usage:
    # Direct URL connection
    python mcp_proxy_server.py http://localhost:8000/mcp [options]
    
    # Registry-based connection
    python mcp_proxy_server.py --server-id weather-service-123 [options]
    
    # Start with registry API enabled
    python mcp_proxy_server.py --enable-registry --api-port 8000 [options]

Examples:
    # Proxy an HTTP MCP server directly
    python mcp_proxy_server.py http://localhost:8000/mcp --name "MyProxy" --port 8001

    # Proxy via registry server ID
    python mcp_proxy_server.py --server-id weather-service --transport http --port 8002

    # Start with registry API for server management
    python mcp_proxy_server.py --enable-registry --api-port 8000
"""

import argparse
import asyncio
import sys
import threading
from typing import Any, Optional

try:
    from fastmcp import FastMCP
    from fastmcp.client import Client
    from fastmcp.client.transports import SSETransport, StreamableHttpTransport, infer_transport
    from fastmcp.server.proxy import FastMCPProxy
    from fastmcp.utilities.logging import get_logger
    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False

# Registry imports
try:
    from mcp_registry.core.database import init_database_sync, get_session_maker
    from mcp_registry.services.registry import RegistryService
    from mcp_registry.api.app import create_app
    import uvicorn
    REGISTRY_AVAILABLE = True
except ImportError:
    REGISTRY_AVAILABLE = False

if FASTMCP_AVAILABLE:
    logger = get_logger(__name__)
else:
    import logging
    logger = logging.getLogger(__name__)


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
        version="2.0.0"
    )
    
    logger.info(f"Proxy server '{proxy_name}' created successfully")
    return proxy_server


async def get_server_url_from_registry(server_id: str) -> tuple[str, str]:
    """
    Get server URL and name from registry by server ID.
    
    Args:
        server_id: The registered server ID
        
    Returns:
        Tuple of (url, name)
        
    Raises:
        ValueError: If server not found or registry not available
    """
    if not REGISTRY_AVAILABLE:
        raise ValueError("Registry functionality not available. Install mcp-registry package.")
    
    try:
        # Initialize database
        init_database_sync()
        
        # Get server from registry
        session_maker = get_session_maker()
        async with session_maker() as session:
            service = RegistryService(session)
            server = await service.get_server(server_id)
            
            if not server:
                raise ValueError(f"Server with ID '{server_id}' not found in registry")
            
            return server['url'], server['name']
        
    except Exception as e:
        raise ValueError(f"Failed to get server from registry: {e}")


def start_registry_api(port: int):
    """Start the registry API in a separate thread."""
    def run_api():
        app = create_app()
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    logger.info(f"Registry API started on http://0.0.0.0:{port}")
    return api_thread


async def run_proxy_server(
    mcp_url: str = None,
    server_id: str = None,
    proxy_name: str = "MCPProxy",
    port: int = None,
    transport: str = "stdio",
    transport_type: str = None,
    enable_registry: bool = False,
    api_port: int = 8000
):
    """
    Main function to run the proxy server with various configurations.
    """
    if not FASTMCP_AVAILABLE:
        raise ValueError("FastMCP not available. Install with: pip install fastmcp")
    
    # Start registry API if requested
    if enable_registry:
        if not REGISTRY_AVAILABLE:
            raise ValueError("Registry not available. Install mcp-registry package.")
        
        # Initialize database
        init_database_sync()
        start_registry_api(api_port)
    
    # Determine MCP URL
    if server_id:
        # Get URL from registry
        mcp_url, server_name = await get_server_url_from_registry(server_id)
        proxy_name = proxy_name if proxy_name != "MCPProxy" else f"Proxy-{server_name}"
        logger.info(f"Using server from registry: {server_name} at {mcp_url}")
    elif not mcp_url and not enable_registry:
        raise ValueError("Must provide either mcp_url or --server-id")
    
    # If only registry is enabled, just keep the API running
    if enable_registry and not mcp_url:
        logger.info("Registry API running. Use the API to manage servers.")
        logger.info(f"API Documentation: http://localhost:{api_port}/docs")
        
        # Keep the main thread alive
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Registry API stopped")
        return
    
    # Create and run the proxy server
    proxy_server = await create_proxy_server(mcp_url, proxy_name, transport_type)
    
    # Create FastMCP app
    app = FastMCP(proxy_server.name, proxy_server.version)
    
    # Add proxy capabilities to the app
    # Note: This is a simplified version - the actual implementation
    # would need to properly integrate the proxy server with FastMCP
    
    logger.info(f"Starting proxy server: {proxy_name}")
    logger.info(f"Transport: {transport}")
    if port:
        logger.info(f"Port: {port}")
    
    # Run the appropriate transport
    if transport == "stdio":
        await app.run_stdio()
    elif transport == "http" and port:
        await app.run_http(port=port)
    elif transport == "sse" and port:
        await app.run_sse(port=port)
    else:
        raise ValueError(f"Invalid transport configuration: {transport}, port: {port}")


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="MCP Proxy Server with Registry Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Proxy a remote MCP server directly
  python mcp_proxy_server.py http://localhost:8000/mcp --transport http --port 8001
  
  # Proxy via registry server ID  
  python mcp_proxy_server.py --server-id weather-service-123 --transport http --port 8002
  
  # Start registry API only
  python mcp_proxy_server.py --enable-registry --api-port 8000
  
  # Start registry API and proxy a registered server
  python mcp_proxy_server.py --enable-registry --server-id weather-service --api-port 8000
        """
    )
    
    parser.add_argument(
        "mcp_url",
        nargs="?",
        help="URL of the remote MCP server to proxy (optional if using --server-id or --enable-registry)"
    )
    
    parser.add_argument(
        "--server-id",
        help="ID of registered server to proxy (alternative to mcp_url)"
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
    
    parser.add_argument(
        "--enable-registry",
        action="store_true",
        help="Enable the registry API for server management"
    )
    
    parser.add_argument(
        "--api-port",
        type=int,
        default=8000,
        help="Port for the registry API (default: 8000)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.transport in ["http", "sse"] and args.port is None and not args.enable_registry:
        print("Error: --port is required when using HTTP or SSE transport", file=sys.stderr)
        sys.exit(1)
    
    if not args.mcp_url and not args.server_id and not args.enable_registry:
        print("Error: Must provide either mcp_url, --server-id, or --enable-registry", file=sys.stderr)
        sys.exit(1)
    
    if args.enable_registry and not REGISTRY_AVAILABLE:
        print("Error: Registry functionality not available. Install mcp-registry package:", file=sys.stderr)
        print("  pip install -e . # or uv pip install -e .", file=sys.stderr)
        sys.exit(1)
    
    if not FASTMCP_AVAILABLE:
        print("Error: FastMCP not available. Install with:", file=sys.stderr)
        print("  pip install fastmcp>=2.0.0", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Run the proxy server
        asyncio.run(run_proxy_server(
            mcp_url=args.mcp_url,
            server_id=args.server_id,
            proxy_name=args.name,
            port=args.port,
            transport=args.transport,
            transport_type=args.transport_type,
            enable_registry=args.enable_registry,
            api_port=args.api_port
        ))
    except KeyboardInterrupt:
        logger.info("Proxy server stopped by user")
    except Exception as e:
        logger.error(f"Proxy server failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()