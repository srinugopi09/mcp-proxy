"""
Server management endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_session
from ...models.server import ServerCreate, ServerUpdate, ServerResponse
from ...services.registry import RegistryService

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


@router.post("/", response_model=ServerResponse)
async def create_server(
    server_data: ServerCreate,
    session: AsyncSession = Depends(get_session)
) -> ServerResponse:
    """Register a new server."""
    service = RegistryService(session)
    server = await service.create_server(server_data)
    return ServerResponse.model_validate(server)


@router.get("/{server_id}", response_model=ServerResponse)
async def get_server(
    server_id: str,
    session: AsyncSession = Depends(get_session)
) -> ServerResponse:
    """Get server by ID."""
    service = RegistryService(session)
    server = await service.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return ServerResponse.model_validate(server)


@router.put("/{server_id}", response_model=ServerResponse)
async def update_server(
    server_id: str,
    server_data: ServerUpdate,
    session: AsyncSession = Depends(get_session)
) -> ServerResponse:
    """Update server information."""
    service = RegistryService(session)
    server = await service.update_server(server_id, server_data)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return ServerResponse.model_validate(server)


@router.delete("/{server_id}")
async def delete_server(
    server_id: str,
    session: AsyncSession = Depends(get_session)
) -> dict:
    """Delete a server."""
    service = RegistryService(session)
    success = await service.delete_server(server_id)
    if not success:
        raise HTTPException(status_code=404, detail="Server not found")
    return {"message": "Server deleted successfully"}