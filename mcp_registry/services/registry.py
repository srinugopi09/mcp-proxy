"""
Registry service for managing MCP servers.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.server import ServerCreate, ServerUpdate
from ..repositories.server import ServerRepository


class RegistryService:
    """Service for managing MCP server registry."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.server_repo = ServerRepository(session)
    
    async def list_servers(self, skip: int = 0, limit: int = 100) -> List[dict]:
        """List all registered servers."""
        return await self.server_repo.list_servers(skip=skip, limit=limit)
    
    async def get_server(self, server_id: str) -> Optional[dict]:
        """Get server by ID."""
        return await self.server_repo.get_server(server_id)
    
    async def create_server(self, server_data: ServerCreate) -> dict:
        """Create a new server registration."""
        return await self.server_repo.create_server(server_data)
    
    async def update_server(self, server_id: str, server_data: ServerUpdate) -> Optional[dict]:
        """Update server information."""
        return await self.server_repo.update_server(server_id, server_data)
    
    async def delete_server(self, server_id: str) -> bool:
        """Delete a server registration."""
        return await self.server_repo.delete_server(server_id)