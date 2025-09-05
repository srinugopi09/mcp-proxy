"""
FastAPI endpoints for MCP server registry.

Provides REST API for server registration, discovery, and management.
"""

from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .models import (
    ServerCreate, ServerUpdate, ServerResponse, ServerCapability,
    CapabilityDiscoveryRequest, CapabilityDiscoveryResponse,
    CapabilitySearchRequest, CapabilitySearchResponse,
    ServerWithCapabilities
)
from .database import Database, get_database
from .capability_discovery import CapabilityDiscoveryService


def create_registry_app(db_path: str = None) -> FastAPI:
    """Create FastAPI application for registry endpoints."""
    
    app = FastAPI(
        title="MCP Server Registry",
        description="Registry and discovery service for Model Context Protocol servers",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )
    
    # Initialize database and services
    database = get_database(db_path)
    discovery_service = CapabilityDiscoveryService(database)
    
    def get_db() -> Database:
        """Dependency to get database instance."""
        return database
    
    def get_discovery_service() -> CapabilityDiscoveryService:
        """Dependency to get capability discovery service."""
        return discovery_service
    
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
    
    @app.get("/api/servers/{server_id}/info", response_model=ServerResponse)
    async def get_server_info(
        server_id: str,
        db: Database = Depends(get_db)
    ) -> ServerResponse:
        """Get detailed server information including server-introspected data."""
        try:
            server = db.get_server(server_id)
            if not server:
                raise HTTPException(status_code=404, detail=f"Server {server_id} not found")
            
            # This endpoint returns the same data as get_server but is explicitly for detailed info
            # The ServerResponse model now includes all the enhanced fields
            return ServerResponse(**server.to_dict())
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get server info: {str(e)}")
    
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
    
    # Capability Discovery Endpoints
    
    @app.post("/api/servers/{server_id}/discover", response_model=CapabilityDiscoveryResponse)
    async def discover_server_capabilities(
        server_id: str,
        request: CapabilityDiscoveryRequest = CapabilityDiscoveryRequest(),
        db: Database = Depends(get_db),
        discovery: CapabilityDiscoveryService = Depends(get_discovery_service)
    ) -> CapabilityDiscoveryResponse:
        """Trigger capability discovery for a specific server."""
        try:
            # Get server details
            server = db.get_server(server_id)
            if not server:
                raise HTTPException(status_code=404, detail=f"Server {server_id} not found")
            
            # Discover capabilities
            result = await discovery.discover_server_capabilities(
                server_id=server_id,
                server_url=server.url,
                transport_type=server.transport,
                timeout_seconds=request.timeout_seconds,
                force_refresh=request.force_refresh
            )
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")
    
    @app.get("/api/servers/{server_id}/capabilities", response_model=List[ServerCapability])
    async def get_server_capabilities(
        server_id: str,
        capability_type: Optional[str] = Query(None, description="Filter by capability type"),
        db: Database = Depends(get_db)
    ) -> List[ServerCapability]:
        """Get all capabilities for a specific server."""
        try:
            server = db.get_server(server_id)
            if not server:
                raise HTTPException(status_code=404, detail=f"Server {server_id} not found")
            
            capabilities = db.get_server_capabilities(server_id, capability_type)
            return [ServerCapability(**cap.to_dict()) for cap in capabilities]
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get capabilities: {str(e)}")
    
    @app.get("/api/servers/{server_id}/tools", response_model=List[ServerCapability])
    async def get_server_tools(
        server_id: str,
        db: Database = Depends(get_db)
    ) -> List[ServerCapability]:
        """Get tools for a specific server."""
        return await get_server_capabilities(server_id, "tool", db)
    
    @app.get("/api/servers/{server_id}/resources", response_model=List[ServerCapability])
    async def get_server_resources(
        server_id: str,
        db: Database = Depends(get_db)
    ) -> List[ServerCapability]:
        """Get resources for a specific server."""
        return await get_server_capabilities(server_id, "resource", db)
    
    @app.get("/api/servers/{server_id}/prompts", response_model=List[ServerCapability])
    async def get_server_prompts(
        server_id: str,
        db: Database = Depends(get_db)
    ) -> List[ServerCapability]:
        """Get prompts for a specific server."""
        return await get_server_capabilities(server_id, "prompt", db)
    
    @app.get("/api/servers/{server_id}/resource-templates", response_model=List[ServerCapability])
    async def get_server_resource_templates(
        server_id: str,
        db: Database = Depends(get_db)
    ) -> List[ServerCapability]:
        """Get resource templates for a specific server."""
        return await get_server_capabilities(server_id, "resource_template", db)
    
    @app.get("/api/servers/{server_id}/discovery-history")
    async def get_discovery_history(
        server_id: str,
        limit: int = Query(10, ge=1, le=100, description="Maximum number of history entries"),
        db: Database = Depends(get_db)
    ) -> List[Dict[str, Any]]:
        """Get capability discovery history for a server."""
        try:
            server = db.get_server(server_id)
            if not server:
                raise HTTPException(status_code=404, detail=f"Server {server_id} not found")
            
            history = db.get_discovery_history(server_id, limit)
            return [discovery.to_dict() for discovery in history]
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get discovery history: {str(e)}")
    
    # Search and Filter Endpoints
    
    @app.get("/api/capabilities/search", response_model=CapabilitySearchResponse)
    async def search_capabilities(
        q: Optional[str] = Query(None, description="Search query"),
        type: Optional[str] = Query(None, description="Filter by capability type"),
        server_id: Optional[str] = Query(None, description="Filter by server ID"),
        limit: int = Query(50, ge=1, le=1000, description="Maximum results to return"),
        offset: int = Query(0, ge=0, description="Number of results to skip"),
        db: Database = Depends(get_db)
    ) -> CapabilitySearchResponse:
        """Search capabilities across all servers."""
        try:
            capabilities, total = db.search_capabilities(
                query=q,
                capability_type=type,
                server_id=server_id,
                limit=limit,
                offset=offset
            )
            
            # Get server names for the response
            server_ids = list(set(cap.server_id for cap in capabilities))
            servers = {}
            for sid in server_ids:
                server = db.get_server(sid)
                if server:
                    servers[sid] = server.name
            
            return CapabilitySearchResponse(
                total=total,
                capabilities=[ServerCapability(**cap.to_dict()) for cap in capabilities],
                servers=servers
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
    
    @app.get("/api/capabilities/tools", response_model=List[ServerCapability])
    async def get_all_tools(
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
        db: Database = Depends(get_db)
    ) -> List[ServerCapability]:
        """Get all tools across all servers."""
        capabilities, _ = db.search_capabilities(
            capability_type="tool",
            limit=limit,
            offset=offset
        )
        return [ServerCapability(**cap.to_dict()) for cap in capabilities]
    
    @app.get("/api/capabilities/stats")
    async def get_capability_stats(
        db: Database = Depends(get_db)
    ) -> Dict[str, Any]:
        """Get capability statistics across all servers."""
        try:
            return db.get_capability_stats()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get capability stats: {str(e)}")
    
    # Enhanced server listing with capabilities
    
    @app.get("/api/servers/with-capabilities", response_model=List[ServerWithCapabilities])
    async def list_servers_with_capabilities(
        status: Optional[str] = Query(None, description="Filter by server status"),
        has_tool: Optional[str] = Query(None, description="Filter servers that have a specific tool"),
        has_capability_type: Optional[str] = Query(None, description="Filter servers with specific capability type"),
        limit: Optional[int] = Query(None, ge=1, le=1000),
        offset: int = Query(0, ge=0),
        db: Database = Depends(get_db),
        discovery: CapabilityDiscoveryService = Depends(get_discovery_service)
    ) -> List[ServerWithCapabilities]:
        """List servers with their capability information."""
        try:
            # Get servers
            servers = db.list_servers(status=status, limit=limit, offset=offset)
            
            # Enhance with capability information
            enhanced_servers = []
            for server in servers:
                # Get capability summary
                summary = discovery.get_server_capabilities_summary(server.id)
                
                # Get latest discovery info
                history = db.get_discovery_history(server.id, limit=1)
                last_discovery = history[0] if history else None
                
                # Apply filters
                if has_tool:
                    tools = db.get_server_capabilities(server.id, "tool")
                    if not any(tool.name == has_tool for tool in tools):
                        continue
                
                if has_capability_type:
                    capabilities = db.get_server_capabilities(server.id, has_capability_type)
                    if not capabilities:
                        continue
                
                enhanced_server = ServerWithCapabilities(
                    **server.to_dict(),
                    capabilities_count=summary["total"],
                    tools_count=summary["by_type"].get("tool", 0),
                    resources_count=summary["by_type"].get("resource", 0),
                    prompts_count=summary["by_type"].get("prompt", 0),
                    resource_templates_count=summary["by_type"].get("resource_template", 0),
                    last_discovery=last_discovery.discovered_at if last_discovery else None,
                    discovery_status=last_discovery.status if last_discovery else None
                )
                enhanced_servers.append(enhanced_server)
            
            return enhanced_servers
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to list servers with capabilities: {str(e)}")
    
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