"""
Server management endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import datetime, UTC
from ...core.database import get_session
from ...models.server import ServerCreate, ServerUpdate, ServerResponse
from ...models.capability import CapabilityResponse
from ...models.base import ErrorResponse
from ...services.registry import RegistryService
from ...services.discovery import DiscoveryService

router = APIRouter()





@router.get("/", response_model=List[ServerResponse])
async def list_servers(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session)
) -> List[ServerResponse]:
    """List all registered servers."""
    service = RegistryService(session)
    servers = await service.list_servers(skip=skip, limit=limit)
    return [ServerResponse.model_validate(server) for server in servers]


@router.post("/", response_model=ServerResponse, status_code=201)
async def create_server(
    server_data: ServerCreate,
    session: AsyncSession = Depends(get_session)
) -> ServerResponse:
    """Register a new server."""
    service = RegistryService(session)
    server = await service.create_server(server_data)
    return ServerResponse.model_validate(server)


@router.get("/{server_id}", response_model=ServerResponse, responses={404: {"model": ErrorResponse}})
async def get_server(
    server_id: str = Path(..., min_length=1, max_length=255, description="Server ID"),
    session: AsyncSession = Depends(get_session)
) -> ServerResponse:
    """Get server by ID."""
    service = RegistryService(session)
    server = await service.get_server(server_id)
    if not server:
        raise HTTPException(
            status_code=404, 
            detail={
                "error": "SERVER_NOT_FOUND",
                "message": f"Server with ID '{server_id}' not found",
                "timestamp": datetime.now(UTC).isoformat()
            }
        )
    return ServerResponse.model_validate(server)


@router.put("/{server_id}", response_model=ServerResponse, responses={404: {"model": ErrorResponse}})
async def update_server(
    server_data: ServerUpdate,
    server_id: str = Path(..., min_length=1, max_length=255, description="Server ID"),
    session: AsyncSession = Depends(get_session)
) -> ServerResponse:
    """Update server information."""
    service = RegistryService(session)
    server = await service.update_server(server_id, server_data)
    if not server:
        raise HTTPException(
            status_code=404, 
            detail={
                "error": "SERVER_NOT_FOUND",
                "message": f"Server with ID '{server_id}' not found",
                "timestamp": datetime.now(UTC).isoformat()
            }
        )
    return ServerResponse.model_validate(server)


@router.delete("/{server_id}", responses={404: {"model": ErrorResponse}})
async def delete_server(
    server_id: str = Path(..., min_length=1, max_length=255, description="Server ID"),
    session: AsyncSession = Depends(get_session)
) -> dict:
    """Delete a server."""
    service = RegistryService(session)
    success = await service.delete_server(server_id)
    if not success:
        raise HTTPException(
            status_code=404, 
            detail={
                "error": "SERVER_NOT_FOUND",
                "message": f"Server with ID '{server_id}' not found",
                "timestamp": datetime.now(UTC).isoformat()
            }
        )
    return {"message": "Server deleted successfully"}


@router.post("/{server_id}/discover", response_model=dict)
async def discover_server_capabilities(
    server_id: str = Path(..., min_length=1, max_length=255, description="Server ID"),
    session: AsyncSession = Depends(get_session)
) -> dict:
    """Discover capabilities for a specific server."""
    service = DiscoveryService(session)
    result = await service.discover_server_capabilities(server_id)
    return {"server_id": server_id, "capabilities": result}


@router.get("/{server_id}/capabilities", response_model=List[CapabilityResponse])
async def get_server_capabilities(
    server_id: str = Path(..., min_length=1, max_length=255, description="Server ID"),
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session)
) -> List[CapabilityResponse]:
    """Get capabilities for a specific server."""
    service = DiscoveryService(session)
    capabilities = await service.get_server_capabilities(server_id, skip=skip, limit=limit)
    return [CapabilityResponse.model_validate(cap) for cap in capabilities]