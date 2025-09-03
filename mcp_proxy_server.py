#!/usr/bin/env python3
"""
MCP Proxy Server with Registry

A standalone FastMCP server that acts as a proxy to any remote MCP server.
Can connect directly via URL or through a server registry for discovery.

Usage:
    # Direct URL connection
    python mcp_proxy_server.py http://localhost:8000/mcp [options]
    
    # Registry-based connection
    python mcp_proxy_server.py --server-id weather-service-123 [options]
    
    # Start with registry API enabled
    python mcp_proxy_server.py --enable-registry --api-port 8080 [options]

Examples:
    # Proxy an HTTP MCP server directly
    python mcp_proxy_server.py http://localhost:8000/mcp --name "MyProxy" --port 8001

    # Proxy via registry server ID
    python mcp_proxy_server.py --server-id weather-service --transport http --port 8002

    # Start with registry API for server management
    python mcp_proxy_server.py --enable-registry --api-port 8080
"""

import argparse
import asyncio
import sys
import threading
from typing import Any, Optional

from fastmcp import FastMCP
from fastmcp.client import Client
from fastmcp.client.transports import SSETransport, StreamableHttpTransport, infer_transport
from fastmcp.server.proxy import FastMCPProxy
from fastmcp.utilities.logging import get_logger

# Registry imports (optional)
try:
    from registry import get_database, create_registry_app
    import uvicorn
    REGISTRY_AVAILABLE = True
except ImportError:
    REGISTRY_AVAILABLE = False

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


async def get_server_url_from_registry(server_id: str, db_path: str = None) -> tuple[str, str]:
    """
    Get server URL and name from registry by server ID.
    
    Args:
        server_id: The registered server ID
        db_path: Optional database path
        
    Returns:
        Tuple of (url, name)
        
    Raises:
        ValueError: If server not found or registry not available
    """
    if not REGISTRY_AVAILABLE:
        raise ValueError("Registry functionality not available. Install required dependencies.")
    
    try:
        database = get_database(db_path)
        server = database.get_server(server_id)
        
        if not server:
            raise ValueError(f"Server with ID '{server_id}' not found in registry")
        
        return server.url, server.name
        
    except Exception as e:
        raise ValueError(f"Failed to get server from registry: {e}")


async def run_registry_api(api_port: int, db_path: str = None):
    """
    Run the registry API server in a separate thread.
    
    Args:
        api_port: Port to run the API on
        db_path: Optional database path
    """
    if not REGISTRY_AVAILABLE:
        raise ValueError("Registry functionality not available. Install required dependencies.")
    
    app = create_registry_app(db_path)
    
    def run_server():
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=api_port,
            log_level="info",
            access_log=True
        )
    
    # Run API server in a separate thread
    api_thread = threading.Thread(target=run_server, daemon=True)
    api_thread.start()
    
    logger.info(f"Registry API started on http://0.0.0.0:{api_port}")
    logger.info(f"API documentation available at http://0.0.0.0:{api_port}/api/docs")
    
    return api_thread


async def run_proxy_server(
    mcp_url: str = None,
    server_id: str = None,
    proxy_name: str = "MCPProxy", 
    port: int | None = None,
    transport: str = "stdio",
    transport_type: str | None = None,
    enable_registry: bool = False,
    api_port: int = 8080,
    db_path: str = None
):
    """
    Runs the MCP proxy server with the specified configuration.
    
    Args:
        mcp_url: The URL of the remote MCP server to proxy
        server_id: The registry ID of the server to proxy
        proxy_name: Name for the proxy server
        port: Port to run HTTP/SSE server on (ignored for stdio)
        transport: Transport type for the proxy server ('stdio', 'http', 'sse')
        transport_type: Transport type for connecting to remote server
        enable_registry: Whether to enable the registry API
        api_port: Port for the registry API
        db_path: Optional database path
    """
    # Start registry API if enabled
    api_thread = None
    if enable_registry:
        api_thread = await run_registry_api(api_port, db_path)
    
    # Determine the MCP URL to connect to
    if server_id:
        if mcp_url:
            logger.warning("Both server_id and mcp_url provided. Using server_id from registry.")
        
        try:
            mcp_url, server_name = await get_server_url_from_registry(server_id, db_path)
            logger.info(f"Found server '{server_name}' with URL: {mcp_url}")
            if proxy_name == "MCPProxy":  # Use server name if default proxy name
                proxy_name = f"{server_name}Proxy"
        except ValueError as e:
            logger.error(f"Registry lookup failed: {e}")
            sys.exit(1)
    
    elif not mcp_url:
        if enable_registry:
            logger.info("Registry API enabled. Use the API to register servers and then connect via --server-id")
            logger.info(f"Registry API: http://0.0.0.0:{api_port}/api/docs")
            
            # Keep the API running
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("Registry API stopped")
                return
        else:
            logger.error("Either mcp_url or server_id must be provided")
            sys.exit(1)
    
    # Create the proxy server
    proxy_server = await create_proxy_server(mcp_url, proxy_name, transport_type)
    
    # Run the server with the specified transport
    if transport == "stdio":
        logger.info(f"Starting proxy server '{proxy_name}' via stdio")
        await proxy_server.run_async(transport="stdio")
    elif transport == "http":
        if port is None:
            port = 8000
        logger.info(f"Starting proxy server '{proxy_name}' via HTTP on port {port}")
        await proxy_server.run_async(transport="http", port=port)
    elif transport == "sse":
        if port is None:
            port = 8000
        logger.info(f"Starting proxy server '{proxy_name}' via SSE on port {port}")
        await proxy_server.run_async(transport="sse", port=port)
    else:
        raise ValueError(f"Unsupported transport type: {transport}")


def main():
    """Main entry point for the MCP proxy server."""
    parser = argparse.ArgumentParser(
        description="MCP Proxy Server with Registry - Proxy any remote MCP server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Direct URL proxy via stdio (default)
  python mcp_proxy_server.py http://localhost:8000/mcp
  
  # Proxy via HTTP on port 8001
  python mcp_proxy_server.py http://localhost:8000/mcp --transport http --port 8001
  
  # Registry-based proxy
  python mcp_proxy_server.py --server-id weather-service-123 --transport http --port 8002
  
  # Start registry API only
  python mcp_proxy_server.py --enable-registry --api-port 8080
  
  # Start registry API and proxy a registered server
  python mcp_proxy_server.py --enable-registry --server-id weather-service --api-port 8080
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
        default=8080,
        help="Port for the registry API (default: 8080)"
    )
    
    parser.add_argument(
        "--db-path",
        help="Path to SQLite database file (default: ./mcp_registry.db)"
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
        print("Error: Registry functionality not available. Install required dependencies:", file=sys.stderr)
        print("  pip install fastapi uvicorn", file=sys.stderr)
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
            api_port=args.api_port,
            db_path=args.db_path
        ))
    except KeyboardInterrupt:
        logger.info("Proxy server stopped by user")
    except Exception as e:
        logger.error(f"Proxy server failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()