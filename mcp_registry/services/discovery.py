"""
Discovery service for MCP server capabilities using FastMCP.
"""

import asyncio
from datetime import datetime, UTC
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.capability import CapabilitySearchRequest
from ..repositories.capability import CapabilityRepository
from ..repositories.server import ServerRepository
from ..core.exceptions import ServerNotFoundError
from ..core.fastmcp_client import create_fastmcp_client, convert_mcp_capabilities_to_dict


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
        """Discover capabilities for a specific server by connecting to it using FastMCP."""
        # Get server info
        server = await self.server_repo.get_server(server_id)
        if not server:
            raise ServerNotFoundError(f"Server {server_id} not found")
        
        try:
            # Use FastMCP client to discover capabilities
            capabilities = await self._discover_with_fastmcp(server_id, server)
            
            # Store discovered capabilities in database
            await self._store_capabilities(server_id, capabilities)
            
            return capabilities
            
        except Exception as e:
            # Log error and return empty list
            print(f"Failed to discover capabilities for {server_id}: {e}")
            return []
    
    async def _discover_with_fastmcp(self, server_id: str, server: dict) -> List[dict]:
        """Use FastMCP client to discover server capabilities."""
        server_url = server["url"]
        transport_type = server.get("transport", "auto")
        
        try:
            # Create fresh FastMCP client for this operation
            client = create_fastmcp_client(server_url, transport_type)
            
            # Use context manager to establish connection and discover capabilities
            async with client:
                print(f"Connected to {server_url} for capability discovery")
                
                # Discover tools
                try:
                    tools = await client.list_tools()
                    print(f"Discovered {len(tools)} tools from {server_url}")
                except Exception as e:
                    print(f"Failed to discover tools from {server_url}: {e}")
                    tools = []
                
                # Discover resources
                try:
                    resources = await client.list_resources()
                    print(f"Discovered {len(resources)} resources from {server_url}")
                except Exception as e:
                    print(f"Failed to discover resources from {server_url}: {e}")
                    resources = []
                
                # Discover prompts
                try:
                    prompts = await client.list_prompts()
                    print(f"Discovered {len(prompts)} prompts from {server_url}")
                except Exception as e:
                    print(f"Failed to discover prompts from {server_url}: {e}")
                    prompts = []
                
                # Convert to our capability format
                all_capabilities = convert_mcp_capabilities_to_dict(
                    tools, resources, prompts, server_id
                )
                
                print(f"Total capabilities discovered for {server_id}: {len(all_capabilities)}")
                return all_capabilities
            
        except Exception as e:
            raise Exception(f"FastMCP discovery failed for {server_url}: {e}")
    

    
    async def _store_capabilities(self, server_id: str, capabilities: List[dict]) -> None:
        """Store discovered capabilities in database."""
        # TODO: Implement capability storage in database
        # For now, we just return the capabilities without storing them
        # This would require:
        # 1. Remove old capabilities for this server
        # 2. Store new capabilities via capability repository
        # 3. Commit the transaction
        
        print(f"Would store {len(capabilities)} capabilities for server {server_id}")
        # await self.session.commit()
    
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