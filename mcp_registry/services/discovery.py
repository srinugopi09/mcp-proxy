"""
Discovery service for MCP server capabilities.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from fastmcp import FastMCP
    from fastmcp.client import MCPClient
    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False
    # Fallback to httpx for basic functionality
    import httpx

from ..models.capability import CapabilitySearchRequest
from ..repositories.capability import CapabilityRepository
from ..repositories.server import ServerRepository
from ..core.exceptions import ServerNotFoundError


class DiscoveryService:
    """Service for discovering MCP server capabilities."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.capability_repo = CapabilityRepository(session)
        self.server_repo = ServerRepository(session)
    
    async def list_capabilities(self, skip: int = 0, limit: int = 100) -> List[dict]:
        """List all available capabilities."""
        return await self.capability_repo.list_capabilities(skip=skip, limit=limit)
    
    async def search_capabilities(self, search_request: CapabilitySearchRequest) -> List[dict]:
        """Search capabilities by criteria."""
        return await self.capability_repo.search_capabilities(search_request)
    
    async def get_server_capabilities(self, server_id: str, skip: int = 0, limit: int = 100) -> List[dict]:
        """Get capabilities for a specific server."""
        # Get server info first to validate it exists
        server = await self.server_repo.get_server(server_id)
        if not server:
            raise ServerNotFoundError(f"Server {server_id} not found")
        
        # Get capabilities filtered by server_id
        capabilities = await self.capability_repo.list_capabilities(skip=skip, limit=limit)
        return [cap for cap in capabilities if cap.get('server_id') == server_id]
    
    async def discover_server_capabilities(self, server_id: str) -> List[dict]:
        """Discover capabilities for a specific server by connecting to it."""
        # Get server info
        server = await self.server_repo.get_server(server_id)
        if not server:
            raise ServerNotFoundError(f"Server {server_id} not found")
        
        try:
            # Connect to MCP server and discover capabilities
            capabilities = await self._connect_and_discover(server)
            
            # Store discovered capabilities in database
            await self._store_capabilities(server_id, capabilities)
            
            return capabilities
            
        except Exception as e:
            # Log error and return empty list
            print(f"Failed to discover capabilities for {server_id}: {e}")
            return []
    
    async def _connect_and_discover(self, server: dict) -> List[dict]:
        """Connect to MCP server and discover its capabilities."""
        server_url = server["url"]
        
        if FASTMCP_AVAILABLE:
            return await self._discover_with_fastmcp(server)
        else:
            return await self._discover_with_httpx(server)
    
    async def _discover_with_fastmcp(self, server: dict) -> List[dict]:
        """Use FastMCP to discover server capabilities."""
        server_url = server["url"]
        
        try:
            # Create FastMCP client
            client = MCPClient(server_url)
            
            # Initialize connection
            await client.initialize(
                client_info={
                    "name": "mcp-registry",
                    "version": "2.0.0"
                }
            )
            
            all_capabilities = []
            
            # Discover tools
            try:
                tools = await client.list_tools()
                for tool in tools:
                    all_capabilities.append({
                        "id": str(uuid.uuid4()),
                        "name": tool.name,
                        "type": "tool",
                        "description": tool.description or "",
                        "schema": tool.input_schema or {},
                        "metadata": {
                            "discovered_at": datetime.utcnow().isoformat(),
                            "discovery_method": "fastmcp"
                        }
                    })
            except Exception as e:
                print(f"Failed to discover tools: {e}")
            
            # Discover resources
            try:
                resources = await client.list_resources()
                for resource in resources:
                    all_capabilities.append({
                        "id": str(uuid.uuid4()),
                        "name": resource.name or resource.uri,
                        "type": "resource",
                        "description": resource.description or "",
                        "schema": {"uri": resource.uri},
                        "metadata": {
                            "mimeType": getattr(resource, 'mime_type', None),
                            "discovered_at": datetime.utcnow().isoformat(),
                            "discovery_method": "fastmcp"
                        }
                    })
            except Exception as e:
                print(f"Failed to discover resources: {e}")
            
            # Discover prompts
            try:
                prompts = await client.list_prompts()
                for prompt in prompts:
                    all_capabilities.append({
                        "id": str(uuid.uuid4()),
                        "name": prompt.name,
                        "type": "prompt",
                        "description": prompt.description or "",
                        "schema": {"arguments": getattr(prompt, 'arguments', [])},
                        "metadata": {
                            "discovered_at": datetime.utcnow().isoformat(),
                            "discovery_method": "fastmcp"
                        }
                    })
            except Exception as e:
                print(f"Failed to discover prompts: {e}")
            
            # Close connection
            await client.close()
            
            return all_capabilities
            
        except Exception as e:
            raise Exception(f"FastMCP connection failed to {server_url}: {e}")
    
    async def _discover_with_httpx(self, server: dict) -> List[dict]:
        """Fallback: Use httpx for basic JSON-RPC discovery."""
        server_url = server["url"]
        
        try:
            # Create MCP client connection
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Send initialize request
                init_request = {
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "roots": {"listChanged": True},
                            "sampling": {}
                        },
                        "clientInfo": {
                            "name": "mcp-registry",
                            "version": "2.0.0"
                        }
                    }
                }
                
                response = await client.post(server_url, json=init_request)
                response.raise_for_status()
                init_result = response.json()
                
                if "error" in init_result:
                    raise Exception(f"Initialize failed: {init_result['error']}")
                
                # Get server capabilities from initialize response
                server_capabilities = init_result.get("result", {}).get("capabilities", {})
                
                # Discover tools
                tools = await self._discover_tools_httpx(client, server_url)
                
                # Discover resources
                resources = await self._discover_resources_httpx(client, server_url)
                
                # Discover prompts
                prompts = await self._discover_prompts_httpx(client, server_url)
                
                # Combine all capabilities
                all_capabilities = []
                
                # Add tools
                for tool in tools:
                    all_capabilities.append({
                        "id": str(uuid.uuid4()),
                        "name": tool.get("name", ""),
                        "type": "tool",
                        "description": tool.get("description", ""),
                        "schema": tool.get("inputSchema", {}),
                        "metadata": {
                            "server_capabilities": server_capabilities,
                            "discovered_at": datetime.utcnow().isoformat(),
                            "discovery_method": "httpx_fallback"
                        }
                    })
                
                # Add resources
                for resource in resources:
                    all_capabilities.append({
                        "id": str(uuid.uuid4()),
                        "name": resource.get("name", ""),
                        "type": "resource",
                        "description": resource.get("description", ""),
                        "schema": {"uri": resource.get("uri", "")},
                        "metadata": {
                            "mimeType": resource.get("mimeType"),
                            "server_capabilities": server_capabilities,
                            "discovered_at": datetime.utcnow().isoformat(),
                            "discovery_method": "httpx_fallback"
                        }
                    })
                
                # Add prompts
                for prompt in prompts:
                    all_capabilities.append({
                        "id": str(uuid.uuid4()),
                        "name": prompt.get("name", ""),
                        "type": "prompt",
                        "description": prompt.get("description", ""),
                        "schema": {"arguments": prompt.get("arguments", [])},
                        "metadata": {
                            "server_capabilities": server_capabilities,
                            "discovered_at": datetime.utcnow().isoformat(),
                            "discovery_method": "httpx_fallback"
                        }
                    })
                
                return all_capabilities
                
        except Exception as e:
            raise Exception(f"Failed to connect to MCP server {server_url}: {e}")
    
    async def _discover_tools_httpx(self, client: httpx.AsyncClient, server_url: str) -> List[dict]:
        """Discover tools from MCP server."""
        try:
            request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/list"
            }
            
            response = await client.post(server_url, json=request)
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                return []
            
            return result.get("result", {}).get("tools", [])
            
        except Exception:
            return []
    
    async def _discover_resources_httpx(self, client: httpx.AsyncClient, server_url: str) -> List[dict]:
        """Discover resources from MCP server."""
        try:
            request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "resources/list"
            }
            
            response = await client.post(server_url, json=request)
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                return []
            
            return result.get("result", {}).get("resources", [])
            
        except Exception:
            return []
    
    async def _discover_prompts_httpx(self, client: httpx.AsyncClient, server_url: str) -> List[dict]:
        """Discover prompts from MCP server."""
        try:
            request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "prompts/list"
            }
            
            response = await client.post(server_url, json=request)
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                return []
            
            return result.get("result", {}).get("prompts", [])
            
        except Exception:
            return []
    
    async def _store_capabilities(self, server_id: str, capabilities: List[dict]) -> None:
        """Store discovered capabilities in database."""
        # First, remove old capabilities for this server
        # (This would need to be implemented in the repository)
        
        # Then store new capabilities
        for capability in capabilities:
            capability["server_id"] = server_id
            # Store in database via repository
            # (This would need proper implementation)
        
        await self.session.commit()
    
    async def scan_all_servers(self) -> Dict[str, Any]:
        """Scan all registered servers for capabilities."""
        servers = await self.server_repo.list_servers()
        results = {
            "total_servers": len(servers),
            "successful": 0,
            "failed": 0,
            "results": []
        }
        
        for server in servers:
            try:
                capabilities = await self.discover_server_capabilities(server["id"])
                results["results"].append({
                    "server_id": server["id"],
                    "server_name": server["name"],
                    "status": "success",
                    "capabilities_count": len(capabilities)
                })
                results["successful"] += 1
            except Exception as e:
                results["results"].append({
                    "server_id": server["id"],
                    "server_name": server["name"],
                    "status": "failed",
                    "error": str(e)
                })
                results["failed"] += 1
        
        return results