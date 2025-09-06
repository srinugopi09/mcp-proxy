"""
Server repository for database operations.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.server import ServerCreate, ServerUpdate
from ..db.models import Server


class ServerRepository:
    """Repository for server database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def list_servers(self, skip: int = 0, limit: int = 100) -> List[dict]:
        """List all servers with pagination."""
        stmt = select(Server).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        servers = result.scalars().all()
        return [server.to_dict() for server in servers]
    
    async def get_server(self, server_id: str) -> Optional[dict]:
        """Get server by ID."""
        stmt = select(Server).where(Server.id == server_id)
        result = await self.session.execute(stmt)
        server = result.scalar_one_or_none()
        return server.to_dict() if server else None
    
    async def create_server(self, server_data: ServerCreate) -> dict:
        """Create a new server."""
        import uuid
        import json
        
        # Convert Pydantic model to database model fields
        data = server_data.model_dump()
        server = Server(
            id=str(uuid.uuid4()),
            name=data["name"],
            description=data.get("description"),
            url=str(data["url"]),
            tags=json.dumps(data.get("tags", [])),
            transport=data.get("transport", "auto"),
            status="unknown",
            server_metadata=json.dumps(data.get("metadata", {}))
        )
        
        self.session.add(server)
        await self.session.commit()
        await self.session.refresh(server)
        return server.to_dict()
    
    async def update_server(self, server_id: str, server_data: ServerUpdate) -> Optional[dict]:
        """Update server information."""
        stmt = select(Server).where(Server.id == server_id)
        result = await self.session.execute(stmt)
        server = result.scalar_one_or_none()
        
        if not server:
            return None
        
        update_data = server_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(server, field, value)
        
        await self.session.commit()
        await self.session.refresh(server)
        return server.to_dict()
    
    async def delete_server(self, server_id: str) -> bool:
        """Delete a server."""
        stmt = select(Server).where(Server.id == server_id)
        result = await self.session.execute(stmt)
        server = result.scalar_one_or_none()
        
        if not server:
            return False
        
        await self.session.delete(server)
        await self.session.commit()
        return True