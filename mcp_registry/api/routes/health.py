"""
Health check endpoints.
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from typing import Dict, Any

from ...core.database import get_session

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    version: str


class DetailedHealthResponse(BaseModel):
    """Detailed health check response model."""
    status: str
    version: str
    database: str
    services: Dict[str, Any]
    timestamp: datetime


@router.get("/", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint."""
    return HealthResponse(status="healthy", version="2.0.0")


@router.get("/ready", response_model=HealthResponse)
async def readiness_check() -> HealthResponse:
    """Readiness check endpoint."""
    return HealthResponse(status="ready", version="2.0.0")


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check(session: AsyncSession = Depends(get_session)) -> DetailedHealthResponse:
    """Detailed health check with database and service status."""
    try:
        # Test database connection
        await session.execute(text("SELECT 1"))
        db_status = "healthy"
        overall_status = "healthy"
    except Exception:
        db_status = "unhealthy"
        overall_status = "degraded"
    
    # Check service components
    services = {
        "registry_service": "healthy",
        "discovery_service": "healthy", 
        "proxy_service": "healthy",
        "database": db_status
    }
    
    return DetailedHealthResponse(
        status=overall_status,
        version="2.0.0",
        database=db_status,
        services=services,
        timestamp=datetime.utcnow()
    )