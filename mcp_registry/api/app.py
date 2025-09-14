"""
FastAPI application factory for MCP Registry.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..core.config import get_settings
from ..core.database import init_database
from .routes.servers import router as servers_router
from .routes.capabilities import router as capabilities_router
from .routes.health import router as health_router
from .routes.proxy import router as proxy_router
from .routes.discovery import router as discovery_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    settings = get_settings()
    
    # Initialize database
    await init_database(settings.database_url)
    
    yield
    
    # Cleanup if needed
    pass


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="MCP Registry API",
        description="Enterprise Model Context Protocol Server Registry",
        version="2.0.0",
        docs_url="/docs",  # Always enable docs for development
        redoc_url="/redoc",  # Always enable redoc for development
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers with API versioning
    app.include_router(discovery_router, prefix="/api/v1", tags=["discovery"])
    app.include_router(health_router, prefix="/api/v1/health", tags=["health"])
    app.include_router(servers_router, prefix="/api/v1/servers", tags=["servers"])
    app.include_router(capabilities_router, prefix="/api/v1/capabilities", tags=["capabilities"])
    app.include_router(proxy_router, prefix="/api/v1/proxy", tags=["proxy"])
    
    return app