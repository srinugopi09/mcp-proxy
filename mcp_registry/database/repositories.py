"""
Repository pattern for database operations.

Clean abstraction layer for database access with async support.
"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import Server, Capability, CapabilityDiscovery
from ..models.server import ServerCreate, ServerUpdate, ServerStatus, TransportType
from ..models.capability import CapabilityType
from ..core.exceptions import ServerNotFoundError, ServerAlreadyExistsError


class BaseRepository:
    """Base repository with common functionality."""
    
    def __init__(self, session: AsyncSession):
        self.session = session


class ServerRepository(BaseRepository):
    """Repository for server operations."""
    
    async def create(self, server_data: ServerCreate) -> Server:
        """Create a new server."""
        # Check if URL already exists
        existing = await self.get_by_url(str(server_data.url))
        if existing:
            raise ServerAlreadyExistsError(str(server_data.url), existing.id)
        
        server = Server(
            name=server_data.name,
            url=str(server_data.url),
            description=server_data.description,
            tags=json.dumps(server_data.tags),
            transport=server_data.transport.value,
            metadata=json.dumps(server_data.metadata)
        )
        
        self.session.add(server)
        await self.session.commit()
        await self.session.refresh(server)
        return server
    
    async def get_by_id(self, server_id: str) -> Optional[Server]:
        """Get server by ID."""
        result = await self.session.execute(
            select(Server).where(Server.id == server_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_url(self, url: str) -> Optional[Server]:
        """Get server by URL."""
        result = await self.session.execute(
            select(Server).where(Server.url == url)
        )
        return result.scalar_one_or_none()
    
    async def update(self, server_id: str, server_data: ServerUpdate) -> Server:
        """Update an existing server."""
        server = await self.get_by_id(server_id)
        if not server:
            raise ServerNotFoundError(server_id)
        
        # Check URL conflicts if URL is being updated
        if server_data.url and str(server_data.url) != server.url:
            existing = await self.get_by_url(str(server_data.url))
            if existing and existing.id != server_id:
                raise ServerAlreadyExistsError(str(server_data.url), existing.id)
        
        # Update fields
        update_data = server_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "url" and value:
                setattr(server, field, str(value))
            elif field in ["tags", "metadata"] and value is not None:
                setattr(server, field, json.dumps(value))
            elif field == "transport" and value:
                setattr(server, field, value.value)
            elif value is not None:
                setattr(server, field, value)
        
        await self.session.commit()
        await self.session.refresh(server)
        return server
    
    async def delete(self, server_id: str) -> bool:
        """Delete a server."""
        server = await self.get_by_id(server_id)
        if not server:
            return False
        
        await self.session.delete(server)
        await self.session.commit()
        return True
    
    async def list_servers(
        self,
        status: Optional[ServerStatus] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Server]:
        """List servers with optional filtering."""
        query = select(Server)
        
        # Apply filters
        if status:
            query = query.where(Server.status == status.value)
        
        if tags:
            # Filter by tags (JSON contains)
            for tag in tags:
                query = query.where(Server.tags.contains(f'"{tag}"'))
        
        # Apply pagination
        query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        # Order by creation date
        query = query.order_by(desc(Server.created_at))
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def update_status(
        self, 
        server_id: str, 
        status: ServerStatus,
        last_checked: Optional[datetime] = None
    ) -> bool:
        """Update server health status."""
        server = await self.get_by_id(server_id)
        if not server:
            return False
        
        server.status = status.value
        server.last_checked = last_checked or datetime.utcnow()
        
        await self.session.commit()
        return True
    
    async def update_server_info(
        self,
        server_id: str,
        server_name: Optional[str] = None,
        server_version: Optional[str] = None,
        protocol_version: Optional[str] = None,
        server_capabilities: Optional[Dict[str, Any]] = None,
        implementation_info: Optional[Dict[str, Any]] = None,
        response_time_ms: Optional[int] = None
    ) -> bool:
        """Update server introspected information."""
        server = await self.get_by_id(server_id)
        if not server:
            return False
        
        # Update server information
        if server_name is not None:
            server.server_name = server_name
        if server_version is not None:
            server.server_version = server_version
        if protocol_version is not None:
            server.protocol_version = protocol_version
        if server_capabilities is not None:
            server.server_capabilities = json.dumps(server_capabilities)
        if implementation_info is not None:
            server.implementation_info = json.dumps(implementation_info)
        
        # Update performance metrics
        if response_time_ms is not None:
            server.last_ping_time = datetime.utcnow()
            
            # Update average response time (simple moving average)
            if server.total_discoveries > 0:
                current_avg = server.avg_response_time_ms
                total = server.total_discoveries
                new_avg = ((current_avg * total) + response_time_ms) // (total + 1)
                server.avg_response_time_ms = new_avg
            else:
                server.avg_response_time_ms = response_time_ms
        
        await self.session.commit()
        return True
    
    async def update_discovery_stats(
        self, 
        server_id: str, 
        success: bool = True
    ) -> bool:
        """Update discovery statistics."""
        server = await self.get_by_id(server_id)
        if not server:
            return False
        
        server.total_discoveries += 1
        if success:
            server.successful_discoveries += 1
        
        await self.session.commit()
        return True
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        # Total servers
        total_result = await self.session.execute(
            select(func.count(Server.id))
        )
        total = total_result.scalar()
        
        # Status breakdown
        status_result = await self.session.execute(
            select(Server.status, func.count(Server.id))
            .group_by(Server.status)
        )
        status_counts = dict(status_result.all())
        
        # Transport breakdown
        transport_result = await self.session.execute(
            select(Server.transport, func.count(Server.id))
            .group_by(Server.transport)
        )
        transport_counts = dict(transport_result.all())
        
        return {
            "total_servers": total,
            "status_breakdown": status_counts,
            "transport_breakdown": transport_counts,
        }


class CapabilityRepository(BaseRepository):
    """Repository for capability operations."""
    
    async def store_capabilities(
        self, 
        server_id: str, 
        capabilities_data: List[Dict[str, Any]]
    ) -> int:
        """Store discovered capabilities for a server."""
        # Delete existing capabilities for this server
        await self.session.execute(
            select(Capability).where(Capability.server_id == server_id)
        )
        existing_capabilities = await self.session.execute(
            select(Capability).where(Capability.server_id == server_id)
        )
        for capability in existing_capabilities.scalars():
            await self.session.delete(capability)
        
        # Insert new capabilities
        stored_count = 0
        for cap_data in capabilities_data:
            capability = Capability(
                server_id=server_id,
                type=cap_data["type"],
                name=cap_data["name"],
                description=cap_data.get("description"),
                input_schema=json.dumps(cap_data.get("input_schema", {})),
                output_schema=json.dumps(cap_data.get("output_schema", {})),
                uri_template=cap_data.get("uri_template"),
                discovered_at=cap_data.get("discovered_at", datetime.utcnow())
            )
            self.session.add(capability)
            stored_count += 1
        
        await self.session.commit()
        return stored_count
    
    async def get_server_capabilities(
        self, 
        server_id: str, 
        capability_type: Optional[CapabilityType] = None
    ) -> List[Capability]:
        """Get capabilities for a server."""
        query = select(Capability).where(Capability.server_id == server_id)
        
        if capability_type:
            query = query.where(Capability.type == capability_type.value)
        
        query = query.order_by(Capability.type, Capability.name)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def search_capabilities(
        self,
        query: Optional[str] = None,
        capability_type: Optional[CapabilityType] = None,
        server_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Capability], int]:
        """Search capabilities with optional filters."""
        base_query = select(Capability)
        count_query = select(func.count(Capability.id))
        
        # Apply filters
        conditions = []
        
        if query:
            conditions.append(
                or_(
                    Capability.name.contains(query),
                    Capability.description.contains(query)
                )
            )
        
        if capability_type:
            conditions.append(Capability.type == capability_type.value)
        
        if server_id:
            conditions.append(Capability.server_id == server_id)
        
        if conditions:
            filter_condition = and_(*conditions)
            base_query = base_query.where(filter_condition)
            count_query = count_query.where(filter_condition)
        
        # Get total count
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()
        
        # Get results with pagination
        base_query = base_query.order_by(Capability.type, Capability.name)
        base_query = base_query.offset(offset).limit(limit)
        
        result = await self.session.execute(base_query)
        capabilities = list(result.scalars().all())
        
        return capabilities, total
    
    async def get_capability_stats(self) -> Dict[str, Any]:
        """Get capability statistics."""
        # Total capabilities
        total_result = await self.session.execute(
            select(func.count(Capability.id))
        )
        total = total_result.scalar()
        
        # Capability type breakdown
        type_result = await self.session.execute(
            select(Capability.type, func.count(Capability.id))
            .group_by(Capability.type)
        )
        type_counts = dict(type_result.all())
        
        # Servers with capabilities
        servers_result = await self.session.execute(
            select(func.count(func.distinct(Capability.server_id)))
        )
        servers_with_capabilities = servers_result.scalar()
        
        return {
            "total_capabilities": total,
            "capability_counts": type_counts,
            "servers_with_capabilities": servers_with_capabilities,
        }


class DiscoveryRepository(BaseRepository):
    """Repository for discovery operations."""
    
    async def record_discovery_attempt(
        self,
        server_id: str,
        status: str,
        capabilities_found: int = 0,
        error_message: Optional[str] = None,
        discovery_time_ms: Optional[int] = None
    ) -> CapabilityDiscovery:
        """Record a capability discovery attempt."""
        discovery = CapabilityDiscovery(
            server_id=server_id,
            status=status,
            capabilities_found=capabilities_found,
            error_message=error_message,
            discovery_time_ms=discovery_time_ms,
            discovered_at=datetime.utcnow()
        )
        
        self.session.add(discovery)
        await self.session.commit()
        await self.session.refresh(discovery)
        return discovery
    
    async def get_discovery_history(
        self, 
        server_id: str, 
        limit: int = 10
    ) -> List[CapabilityDiscovery]:
        """Get discovery history for a server."""
        query = (
            select(CapabilityDiscovery)
            .where(CapabilityDiscovery.server_id == server_id)
            .order_by(desc(CapabilityDiscovery.discovered_at))
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        return list(result.scalars().all())