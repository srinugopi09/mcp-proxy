"""
Capability repository for database operations.
"""

from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.capability import CapabilitySearchRequest
from ..db.models import Capability


class CapabilityRepository:
    """Repository for capability database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def list_capabilities(self, skip: int = 0, limit: int = 100) -> List[dict]:
        """List all capabilities with pagination."""
        stmt = select(Capability).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        capabilities = result.scalars().all()
        return [cap.to_dict() for cap in capabilities]
    
    async def search_capabilities(self, search_request: CapabilitySearchRequest) -> List[dict]:
        """Search capabilities by criteria."""
        stmt = select(Capability)
        
        if search_request.capability_type:
            stmt = stmt.where(Capability.type == search_request.capability_type)
        
        if search_request.name:
            stmt = stmt.where(Capability.name.ilike(f"%{search_request.name}%"))
        
        result = await self.session.execute(stmt)
        capabilities = result.scalars().all()
        return [cap.to_dict() for cap in capabilities]
    
    async def discover_server_capabilities(self, server_id: str) -> List[dict]:
        """Discover capabilities for a specific server."""
        stmt = select(Capability).where(Capability.server_id == server_id)
        result = await self.session.execute(stmt)
        capabilities = result.scalars().all()
        return [cap.to_dict() for cap in capabilities]