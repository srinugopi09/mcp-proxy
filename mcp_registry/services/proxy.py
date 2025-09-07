"""
MCP Proxy service using FastMCP's built-in proxy functionality.
"""

import asyncio
import json
import uuid
from typing import Dict, Any, Optional, Callable
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from fastmcp import FastMCP
    from fastmcp.client import Client
    from fastmcp.client.transports import SSETransport, StreamableHttpTransport, infer_transport
    from fastmcp.server.proxy import FastMCPProxy
    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False
    # Fallback to httpx
    import httpx

from ..repositories.server import ServerRepository
from ..core.exceptions import ServerNotFoundError


class ProxyService:
    """Service for creating and managing FastMCP proxy servers."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.server_repo = ServerRepository(session)
        self._proxy_servers: Dict[str, FastMCPProxy] = {}
    
    def _create_client_factory(self, mcp_url: str, transport_type: str = None) -> Callable[[], Client]:
        """Create a client factory for the given MCP URL."""
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
        self, 
        server_id: str, 
        proxy_name: str = None
    ) -> FastMCPProxy:
        """Create a FastMCPProxy for a registered server."""
        if not FASTMCP_AVAILABLE:
            raise Exception("FastMCP not available. Cannot create proxy server.")
        
        # Get server info
        server = await self.server_repo.get_server(server_id)
        if not server:
            raise ServerNotFoundError(f"Server {server_id} not found")
        
        mcp_url = server["url"]
        transport_type = server.get("transport", "auto")
        if transport_type == "auto":
            transport_type = None
        
        proxy_name = proxy_name or f"Proxy-{server['name']}"
        
        # Create client factory
        client_factory = self._create_client_factory(mcp_url, transport_type)
        
        # Test connection first
        try:
            test_client = client_factory()
            async with test_client as client:
                # Try to initialize and get server info
                init_result = client.initialize_result
                server_info = init_result.serverInfo
                print(f"Successfully connected to remote server: {server_info.name} v{server_info.version}")
        except Exception as e:
            raise Exception(f"Failed to connect to remote MCP server at {mcp_url}: {e}")
        
        # Create the proxy server
        proxy_server = FastMCPProxy(
            client_factory=client_factory,
            name=proxy_name,
            version="2.0.0"
        )
        
        # Store the proxy server
        self._proxy_servers[server_id] = proxy_server
        
        return proxy_server
    
    async def get_proxy_server(self, server_id: str) -> Optional[FastMCPProxy]:
        """Get existing proxy server or create new one."""
        if server_id in self._proxy_servers:
            return self._proxy_servers[server_id]
        
        try:
            return await self.create_proxy_server(server_id)
        except Exception:
            return None
    
    async def run_proxy_server(
        self, 
        server_id: str, 
        transport: str = "stdio",
        port: int = None,
        proxy_name: str = None
    ) -> None:
        """Run a proxy server for a registered MCP server."""
        proxy_server = await self.create_proxy_server(server_id, proxy_name)
        
        # Create FastMCP app with the proxy
        app = FastMCP(proxy_server.name, proxy_server.version)
        
        # Add all proxy server capabilities
        for tool in proxy_server.list_tools():
            app.add_tool(tool)
        
        for resource in proxy_server.list_resources():
            app.add_resource(resource)
        
        for prompt in proxy_server.list_prompts():
            app.add_prompt(prompt)
        
        # Run the server
        if transport == "stdio":
            await app.run_stdio()
        elif transport == "http" and port:
            await app.run_http(port=port)
        elif transport == "sse" and port:
            await app.run_sse(port=port)
        else:
            raise ValueError(f"Invalid transport configuration: {transport}, port: {port}")
    
    async def proxy_request(
        self, 
        server_id: str, 
        method: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Proxy a JSON-RPC request to a registered MCP server."""
        
        # Get server info
        server = await self.server_repo.get_server(server_id)
        if not server:
            raise ServerNotFoundError(f"Server {server_id} not found")
        
        server_url = server["url"]
        
        # Create JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method
        }
        
        if params:
            request["params"] = params
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(server_url, json=request)
                response.raise_for_status()
                return response.json()
                
        except httpx.RequestError as e:
            return {
                "jsonrpc": "2.0",
                "id": request["id"],
                "error": {
                    "code": -32603,
                    "message": f"Request failed: {str(e)}"
                }
            }
        except httpx.HTTPStatusError as e:
            return {
                "jsonrpc": "2.0", 
                "id": request["id"],
                "error": {
                    "code": -32603,
                    "message": f"HTTP error {e.response.status_code}: {e.response.text}"
                }
            }
    
    async def call_tool(
        self, 
        server_id: str, 
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call a tool on a registered MCP server."""
        # Get server info
        server = await self.server_repo.get_server(server_id)
        if not server:
            raise ServerNotFoundError(f"Server {server_id} not found")
        
        if FASTMCP_AVAILABLE:
            return await self._call_tool_fastmcp(server, tool_name, arguments)
        else:
            return await self.proxy_request(
                server_id,
                "tools/call",
                {
                    "name": tool_name,
                    "arguments": arguments
                }
            )
    
    async def _call_tool_fastmcp(
        self, 
        server: dict, 
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use FastMCP to call a tool."""
        try:
            client = MCPClient(server["url"])
            await client.initialize(
                client_info={
                    "name": "mcp-registry-proxy",
                    "version": "2.0.0"
                }
            )
            
            result = await client.call_tool(tool_name, arguments)
            await client.close()
            
            return {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "result": result
            }
            
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "error": {
                    "code": -32603,
                    "message": f"FastMCP tool call failed: {str(e)}"
                }
            }
    
    async def get_resource(
        self, 
        server_id: str, 
        resource_uri: str
    ) -> Dict[str, Any]:
        """Get a resource from a registered MCP server."""
        # Get server info
        server = await self.server_repo.get_server(server_id)
        if not server:
            raise ServerNotFoundError(f"Server {server_id} not found")
        
        if FASTMCP_AVAILABLE:
            return await self._get_resource_fastmcp(server, resource_uri)
        else:
            return await self.proxy_request(
                server_id,
                "resources/read",
                {
                    "uri": resource_uri
                }
            )
    
    async def _get_resource_fastmcp(
        self, 
        server: dict, 
        resource_uri: str
    ) -> Dict[str, Any]:
        """Use FastMCP to get a resource."""
        try:
            client = MCPClient(server["url"])
            await client.initialize(
                client_info={
                    "name": "mcp-registry-proxy",
                    "version": "2.0.0"
                }
            )
            
            result = await client.read_resource(resource_uri)
            await client.close()
            
            return {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "result": result
            }
            
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "error": {
                    "code": -32603,
                    "message": f"FastMCP resource read failed: {str(e)}"
                }
            }
    
    async def get_prompt(
        self, 
        server_id: str, 
        prompt_name: str, 
        arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get a prompt from a registered MCP server."""
        params = {"name": prompt_name}
        if arguments:
            params["arguments"] = arguments
            
        return await self.proxy_request(
            server_id,
            "prompts/get",
            params
        )
    
    async def initialize_server(self, server_id: str) -> Dict[str, Any]:
        """Initialize connection with a registered MCP server."""
        return await self.proxy_request(
            server_id,
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "mcp-registry-proxy",
                    "version": "2.0.0"
                }
            }
        )