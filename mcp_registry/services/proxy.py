"""
MCP Proxy service for proxying requests to registered MCP servers.
"""

import json
import uuid
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from fastmcp.client import MCPClient
    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False
    # Fallback to httpx
    import httpx

from ..repositories.server import ServerRepository
from ..core.exceptions import ServerNotFoundError


class ProxyService:
    """Service for proxying MCP requests to registered servers."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.server_repo = ServerRepository(session)
    
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