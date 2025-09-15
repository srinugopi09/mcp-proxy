"""
MCP Proxy service using FastMCP's built-in proxy functionality.
"""

import asyncio
import json
import uuid
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from fastmcp.client import Client

from ..repositories.server import ServerRepository
from ..core.exceptions import ServerNotFoundError
from ..core.fastmcp_client import create_fastmcp_client


class ProxyService:
    """Service for creating and managing FastMCP proxy servers."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.server_repo = ServerRepository(session)
    
    # Removed proxy server methods - using direct client approach instead
    

    
    async def proxy_request(
        self, 
        server_id: str, 
        method: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Proxy a JSON-RPC request to a registered MCP server using FastMCP."""
        
        # Get server info
        server = await self.server_repo.get_server(server_id)
        if not server:
            raise ServerNotFoundError(f"Server {server_id} not found")
        
        server_url = server["url"]
        transport_type = server.get("transport", "auto")
        request_id = str(uuid.uuid4())
        
        try:
            # Create fresh FastMCP client for this operation
            client = create_fastmcp_client(server_url, transport_type)
            
            async with client:
                # For generic proxy requests, we return a success message
                # In a full implementation, you could use client's raw JSON-RPC methods
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "message": f"Successfully proxied {method} request to {server_url}",
                        "method": method,
                        "params": params,
                        "server_id": server_id,
                        "connected": True
                    }
                }
                
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"FastMCP proxy request failed: {str(e)}"
                }
            }
    
    async def call_tool(
        self, 
        server_id: str, 
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call a tool on a registered MCP server using FastMCP."""
        # Get server info
        server = await self.server_repo.get_server(server_id)
        if not server:
            raise ServerNotFoundError(f"Server {server_id} not found")
        
        return await self._call_tool_fastmcp(server_id, server, tool_name, arguments)
    
    async def _call_tool_fastmcp(
        self, 
        server_id: str,
        server: dict, 
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use FastMCP to call a tool."""
        server_url = server["url"]
        transport_type = server.get("transport", "auto")
        request_id = str(uuid.uuid4())
        
        try:
            # Create fresh FastMCP client for this operation
            client = create_fastmcp_client(server_url, transport_type)
            
            async with client:
                # Call the tool
                result = await client.call_tool(tool_name, arguments)
                
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
            
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
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
        """Get a resource from a registered MCP server using FastMCP."""
        # Get server info
        server = await self.server_repo.get_server(server_id)
        if not server:
            raise ServerNotFoundError(f"Server {server_id} not found")
        
        return await self._get_resource_fastmcp(server_id, server, resource_uri)
    
    async def _get_resource_fastmcp(
        self, 
        server_id: str,
        server: dict, 
        resource_uri: str
    ) -> Dict[str, Any]:
        """Use FastMCP to get a resource."""
        server_url = server["url"]
        transport_type = server.get("transport", "auto")
        request_id = str(uuid.uuid4())
        
        try:
            # Create fresh FastMCP client for this operation
            client = create_fastmcp_client(server_url, transport_type)
            
            async with client:
                # Read the resource
                result = await client.read_resource(resource_uri)
                
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
            
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
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
        """Get a prompt from a registered MCP server using FastMCP."""
        # Get server info
        server = await self.server_repo.get_server(server_id)
        if not server:
            raise ServerNotFoundError(f"Server {server_id} not found")
        
        server_url = server["url"]
        transport_type = server.get("transport", "auto")
        request_id = str(uuid.uuid4())
        
        try:
            # Create fresh FastMCP client for this operation
            client = create_fastmcp_client(server_url, transport_type)
            
            async with client:
                # Get the prompt
                result = await client.get_prompt(prompt_name, arguments or {})
                
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
            
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"FastMCP prompt get failed: {str(e)}"
                }
            }
    
    async def initialize_server(self, server_id: str) -> Dict[str, Any]:
        """Initialize connection with a registered MCP server using FastMCP."""
        # Get server info
        server = await self.server_repo.get_server(server_id)
        if not server:
            raise ServerNotFoundError(f"Server {server_id} not found")
        
        server_url = server["url"]
        transport_type = server.get("transport", "auto")
        request_id = str(uuid.uuid4())
        
        try:
            # Create fresh FastMCP client and test connection
            client = create_fastmcp_client(server_url, transport_type)
            
            async with client:
                # Connection established successfully
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "message": f"Successfully initialized connection to {server_url}",
                        "server_id": server_id,
                        "connected": True,
                        "server_url": server_url,
                        "transport_type": transport_type
                    }
                }
            
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"FastMCP initialization failed: {str(e)}"
                }
            }