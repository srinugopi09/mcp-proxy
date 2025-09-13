"""FastAPI application factory and configuration."""

from fastapi import FastAPI

from .config import settings
from .routes import router
from .discovery import router as discovery_router
from .health import router as health_router
from .session import hub_state


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title=settings.api_title,
        description=settings.api_description,
        version=settings.api_version,
    )

    # Include API routes with versioning
    app.include_router(discovery_router, prefix="/api/v1", tags=["discovery"])
    app.include_router(health_router, prefix="/api/v1/health", tags=["health"])
    app.include_router(router, prefix="/api/v1", tags=["servers"])

    # Mount the MCP hub under /mcp/
    # FastMCP provides an ASGI app that can be mounted directly
    app.mount("/mcp", hub_state.hub)

    @app.on_event("startup")
    async def startup() -> None:
        """Perform startup tasks such as scheduling the cleanup loop."""
        await hub_state.start_cleanup_task()

    @app.on_event("shutdown")
    async def shutdown() -> None:
        """Perform cleanup tasks on shutdown."""
        await hub_state.stop_cleanup_task()

    return app