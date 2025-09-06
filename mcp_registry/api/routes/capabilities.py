"""
Capability discovery endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_session
from ...models.capability import CapabilityResponse, CapabilitySearchRequest
from ...services.discovery import DiscoveryService

router = APIRouter()


@router.get("/", response_model=List[CapabilityResponse])
async def list_capabilities(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session)
) -> List[CapabilityResponse]:
    """List all available capabilities."""
    service = DiscoveryService(session)
    capabilities = await service.list_capabilities(skip=skip, limit=limit)
    return [CapabilityResponse.model_validate(cap) for cap in capabilities]


@router.post("/search", response_model=List[CapabilityResponse])
async def search_capabilities(
    search_request: CapabilitySearchRequest,
    session: AsyncSession = Depends(get_session)
) -> List[CapabilityResponse]:
    """Search capabilities by criteria."""
    service = DiscoveryService(session)
    capabilities = await service.search_capabilities(search_request)
    return [CapabilityResponse.model_validate(cap) for cap in capabilities]


@router.get("/discover/{server_id}")
async def discover_server_capabilities(
    server_id: str,
    session: AsyncSession = Depends(get_session)
) -> dict:
    """Discover capabilities for a specific server."""
    service = DiscoveryService(session)
    result = await service.discover_server_capabilities(server_id)
    return {"server_id": server_id, "capabilities": result}