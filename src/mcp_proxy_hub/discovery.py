"""API discovery endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict

router = APIRouter()


class APIDiscoveryResponse(BaseModel):
    """API discovery response model."""
    
    version: str
    resources: Dict[str, str]
    documentation: str


@router.get("/", response_model=APIDiscoveryResponse)
async def api_discovery() -> APIDiscoveryResponse:
    """API discovery endpoint providing information about available resources."""
    return APIDiscoveryResponse(
        version="1.0",
        resources={
            "servers": "/api/v1/server",
            "health": "/api/v1/health",
            "mcp": "/mcp"
        },
        documentation="/docs"
    )