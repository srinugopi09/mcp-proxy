"""
Discovery service for MCP server capabilities.
"""

from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.capability import CapabilitySearchRequest
from ..repositories.capability import CapabilityRepository


class DiscoveryService:
    """Service for discovering MCP server capabilities."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.capability_repo = CapabilityRepository(session)
    
    async def list_capabilities(self, skip: int = 0, limit: int = 100) -> List[dict]:
        """List all available capabilities."""
        return await self.capability_repo.list_capabilities(skip=skip, limit=limit)
    
    async def search_capabilities(self, search_request: CapabilitySearchRequest) -> List[dict]:
        """Search capabilities by criteria."""
        return await self.capability_repo.search_capabilities(search_request)
    
    async def discover_server_capabilities(self, server_id: str) -> List[dict]:
        """Discover capabilities for a specific server."""
        return await self.capability_repo.discover_server_capabilities(server_id)