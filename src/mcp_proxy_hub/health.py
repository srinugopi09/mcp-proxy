"""Health check endpoints."""

from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Basic health response model."""
    
    status: str
    timestamp: datetime


class DetailedHealthResponse(BaseModel):
    """Detailed health response model."""
    
    status: str
    version: str
    services: dict
    timestamp: datetime


@router.get("/", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow()
    )


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check() -> DetailedHealthResponse:
    """Detailed health check with service status."""
    from .session import hub_state
    
    # Check server connection manager health
    server_count = len(hub_state.sessions)
    server_status = "healthy" if server_count < 1000 else "degraded"  # Arbitrary threshold
    
    # Check cleanup task status
    cleanup_status = "healthy" if hub_state._cleanup_task and not hub_state._cleanup_task.done() else "stopped"
    
    overall_status = "healthy"
    if server_status == "degraded" or cleanup_status == "stopped":
        overall_status = "degraded"
    
    return DetailedHealthResponse(
        status=overall_status,
        version="0.1.0",
        services={
            "mcp_hub": "healthy",
            "server_manager": server_status,
            "cleanup_task": cleanup_status,
            "active_servers": server_count
        },
        timestamp=datetime.utcnow()
    )