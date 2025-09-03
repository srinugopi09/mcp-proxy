"""
FastAPI endpoints for MCP server registry.

Provides REST API for server registration, discovery, and management.
"""

from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .models import ServerCreate, ServerUpdate, ServerResponse
from .database import Database, get_database


def create_registry_app(db_path: str = None) -> FastAPI:
    """Create FastAPI application for registry endpoints."""
    
    app = FastAPI(
        title="MCP Server Registry",
        description="Registry and discovery service for Model Context Protocol servers",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )
    
    # Initialize database
    database = get_database(db_path)
    
    def get_db() -> Database:
        """Dependency to get database instance."""
        return database
    
    @app.get("/api/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "mcp-registry"}
    
    @app.get("/api/stats")
    async def get_stats(db: Database = Depends(get_db)) -> Dict[str, Any]:
        """Get registry statistics."""
        try:
            stats = db.get_stats()
            return stats
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
    
    @app.post("/api/servers", response_model=ServerResponse, status_code=201)
    async def register_server(
        server_data: ServerCreate,
        db: Database = Depends(get_db)
    ) -> ServerResponse:
        """Register a new MCP server."""
        try:
            # Check if URL already exists
            existing = db.get_server_by_url(str(server_data.url))
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=f"Server with URL {server_data.url} already registered with ID {existing.id}"
                )
            
            # Create new server
            server = db.create_server(server_data)
            return ServerResponse(**server.to_dict())
            
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to register server: {str(e)}")
    
    @app.get("/api/servers", response_model=List[ServerResponse])
    async def list_servers(
        status: Optional[str] = Query(None, description="Filter by server status"),
        tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
        limit: Optional[int] = Query(None, ge=1, le=1000, description="Maximum number of servers to return"),
        offset: int = Query(0, ge=0, description="Number of servers to skip"),
        db: Database = Depends(get_db)
    ) -> List[ServerResponse]:
        """List registered MCP servers with optional filtering."""
        try:
            # Parse tags if provided
            tag_list = None
            if tags:
                tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
            
            servers = db.list_servers(
                status=status,
                tags=tag_list,
                limit=limit,
                offset=offset
            )
            
            return [ServerResponse(**server.to_dict()) for server in servers]
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to list servers: {str(e)}")
    
    @app.get("/api/servers/{server_id}", response_model=ServerResponse)
    async def get_server(
        server_id: str,
        db: Database = Depends(get_db)
    ) -> ServerResponse:
        """Get details of a specific MCP server."""
        try:
            server = db.get_server(server_id)
            if not server:
                raise HTTPException(status_code=404, detail=f"Server {server_id} not found")
            
            return ServerResponse(**server.to_dict())
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get server: {str(e)}")
    
    @app.put("/api/servers/{server_id}", response_model=ServerResponse)
    async def update_server(
        server_id: str,
        server_data: ServerUpdate,
        db: Database = Depends(get_db)
    ) -> ServerResponse:
        """Update an existing MCP server registration."""
        try:
            # Check if URL conflicts with another server (if URL is being updated)
            if server_data.url:
                existing = db.get_server_by_url(str(server_data.url))
                if existing and existing.id != server_id:
                    raise HTTPException(
                        status_code=409,
                        detail=f"URL {server_data.url} already used by server {existing.id}"
                    )
            
            server = db.update_server(server_id, server_data)
            if not server:
                raise HTTPException(status_code=404, detail=f"Server {server_id} not found")
            
            return ServerResponse(**server.to_dict())
            
        except HTTPException:
            raise
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update server: {str(e)}")
    
    @app.delete("/api/servers/{server_id}")
    async def delete_server(
        server_id: str,
        db: Database = Depends(get_db)
    ) -> Dict[str, str]:
        """Delete an MCP server registration."""
        try:
            success = db.delete_server(server_id)
            if not success:
                raise HTTPException(status_code=404, detail=f"Server {server_id} not found")
            
            return {"message": f"Server {server_id} deleted successfully"}
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete server: {str(e)}")
    
    @app.patch("/api/servers/{server_id}/status")
    async def update_server_status(
        server_id: str,
        status_data: Dict[str, str],
        db: Database = Depends(get_db)
    ) -> Dict[str, str]:
        """Update server health status."""
        try:
            if "status" not in status_data:
                raise HTTPException(status_code=422, detail="Status field is required")
            
            status = status_data["status"]
            if status not in ["healthy", "unhealthy", "unknown"]:
                raise HTTPException(
                    status_code=422, 
                    detail="Status must be one of: healthy, unhealthy, unknown"
                )
            
            success = db.update_server_status(server_id, status)
            if not success:
                raise HTTPException(status_code=404, detail=f"Server {server_id} not found")
            
            return {"message": f"Server {server_id} status updated to {status}"}
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update status: {str(e)}")
    
    # Error handlers
    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request, exc):
        return JSONResponse(
            status_code=422,
            content={"detail": "Validation error", "errors": exc.errors()}
        )
    
    @app.exception_handler(404)
    async def not_found_handler(request, exc):
        return JSONResponse(
            status_code=404,
            content={"detail": "Resource not found"}
        )
    
    @app.exception_handler(500)
    async def internal_error_handler(request, exc):
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    
    return app


# Convenience function to create app with default settings
def create_app() -> FastAPI:
    """Create FastAPI app with default database path."""
    return create_registry_app()