"""
Pydantic models for MCP server registry.

Defines the data structures for server registration, updates, and responses.
"""

import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, validator, HttpUrl


class ServerCreate(BaseModel):
    """Model for creating a new MCP server registration."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable server name")
    url: HttpUrl = Field(..., description="MCP server URL")
    description: Optional[str] = Field(None, max_length=1000, description="Server description")
    tags: Optional[List[str]] = Field(default_factory=list, description="Categorization tags")
    transport: Optional[str] = Field("auto", description="Transport type: http, sse, or auto")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('tags')
    def validate_tags(cls, v):
        if v is None:
            return []
        # Remove duplicates and empty strings
        return list(set(tag.strip() for tag in v if tag and tag.strip()))
    
    @validator('transport')
    def validate_transport(cls, v):
        if v not in ['http', 'sse', 'auto']:
            raise ValueError('Transport must be one of: http, sse, auto')
        return v
    
    @validator('url')
    def validate_url_scheme(cls, v):
        if v.scheme not in ['http', 'https']:
            raise ValueError('URL must use http or https scheme')
        return v


class ServerUpdate(BaseModel):
    """Model for updating an existing MCP server registration."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    url: Optional[HttpUrl] = Field(None)
    description: Optional[str] = Field(None, max_length=1000)
    tags: Optional[List[str]] = Field(None)
    transport: Optional[str] = Field(None)
    metadata: Optional[Dict[str, Any]] = Field(None)
    
    @validator('tags')
    def validate_tags(cls, v):
        if v is None:
            return None
        return list(set(tag.strip() for tag in v if tag and tag.strip()))
    
    @validator('transport')
    def validate_transport(cls, v):
        if v is not None and v not in ['http', 'sse', 'auto']:
            raise ValueError('Transport must be one of: http, sse, auto')
        return v
    
    @validator('url')
    def validate_url_scheme(cls, v):
        if v is not None and v.scheme not in ['http', 'https']:
            raise ValueError('URL must use http or https scheme')
        return v


class ServerResponse(BaseModel):
    """Model for server data in API responses."""
    
    id: str = Field(..., description="Auto-generated server ID")
    name: str = Field(..., description="Human-readable server name")
    url: str = Field(..., description="MCP server URL")
    description: Optional[str] = Field(None, description="Server description")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")
    transport: str = Field(..., description="Transport type")
    status: str = Field(..., description="Server health status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(..., description="Registration timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_checked: Optional[datetime] = Field(None, description="Last health check timestamp")
    
    class Config:
        from_attributes = True


class ServerModel:
    """SQLAlchemy-style model for database operations."""
    
    def __init__(
        self,
        id: str = None,
        name: str = None,
        url: str = None,
        description: str = None,
        tags: str = None,  # JSON string in database
        transport: str = "auto",
        status: str = "unknown",
        metadata: str = None,  # JSON string in database
        created_at: datetime = None,
        updated_at: datetime = None,
        last_checked: datetime = None,
    ):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.url = url
        self.description = description
        self.tags = tags or "[]"
        self.transport = transport
        self.status = status
        self.metadata = metadata or "{}"
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.last_checked = last_checked
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "tags": json.loads(self.tags) if self.tags else [],
            "transport": self.transport,
            "status": self.status,
            "metadata": json.loads(self.metadata) if self.metadata else {},
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_checked": self.last_checked,
        }
    
    @classmethod
    def from_create(cls, data: ServerCreate) -> "ServerModel":
        """Create model instance from ServerCreate data."""
        return cls(
            name=data.name,
            url=str(data.url),
            description=data.description,
            tags=json.dumps(data.tags),
            transport=data.transport,
            metadata=json.dumps(data.metadata),
        )
    
    def update_from_data(self, data: ServerUpdate) -> None:
        """Update model instance from ServerUpdate data."""
        if data.name is not None:
            self.name = data.name
        if data.url is not None:
            self.url = str(data.url)
        if data.description is not None:
            self.description = data.description
        if data.tags is not None:
            self.tags = json.dumps(data.tags)
        if data.transport is not None:
            self.transport = data.transport
        if data.metadata is not None:
            self.metadata = json.dumps(data.metadata)
        
        self.updated_at = datetime.utcnow()


# Capability Discovery Models

class CapabilityType(str):
    """Enumeration of MCP capability types."""
    TOOL = "tool"
    RESOURCE = "resource"
    PROMPT = "prompt"
    RESOURCE_TEMPLATE = "resource_template"


class ServerCapability(BaseModel):
    """Model for a discovered server capability."""
    
    id: Optional[int] = Field(None, description="Database ID")
    server_id: str = Field(..., description="Server ID this capability belongs to")
    type: Literal["tool", "resource", "prompt", "resource_template"] = Field(..., description="Capability type")
    name: str = Field(..., description="Capability name")
    description: Optional[str] = Field(None, description="Capability description")
    input_schema: Optional[Dict[str, Any]] = Field(None, description="Input schema (JSON Schema)")
    output_schema: Optional[Dict[str, Any]] = Field(None, description="Output schema (JSON Schema)")
    uri_template: Optional[str] = Field(None, description="URI template for resource templates")
    discovered_at: datetime = Field(default_factory=datetime.utcnow, description="Discovery timestamp")
    
    class Config:
        from_attributes = True


class CapabilityDiscovery(BaseModel):
    """Model for capability discovery attempts."""
    
    id: Optional[int] = Field(None, description="Database ID")
    server_id: str = Field(..., description="Server ID")
    status: Literal["success", "failed", "partial"] = Field(..., description="Discovery status")
    capabilities_found: int = Field(0, description="Number of capabilities discovered")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    discovery_time_ms: Optional[int] = Field(None, description="Discovery time in milliseconds")
    discovered_at: datetime = Field(default_factory=datetime.utcnow, description="Discovery timestamp")
    
    class Config:
        from_attributes = True


class CapabilityDiscoveryRequest(BaseModel):
    """Request model for triggering capability discovery."""
    
    force_refresh: bool = Field(False, description="Force refresh even if recently discovered")
    timeout_seconds: Optional[int] = Field(30, description="Discovery timeout in seconds")


class CapabilityDiscoveryResponse(BaseModel):
    """Response model for capability discovery results."""
    
    server_id: str = Field(..., description="Server ID")
    status: str = Field(..., description="Discovery status")
    capabilities_found: int = Field(..., description="Number of capabilities discovered")
    discovery_time_ms: int = Field(..., description="Discovery time in milliseconds")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    capabilities: List[ServerCapability] = Field(default_factory=list, description="Discovered capabilities")


class CapabilitySearchRequest(BaseModel):
    """Request model for searching capabilities."""
    
    query: Optional[str] = Field(None, description="Search query")
    type: Optional[Literal["tool", "resource", "prompt", "resource_template"]] = Field(None, description="Filter by capability type")
    server_id: Optional[str] = Field(None, description="Filter by server ID")
    limit: Optional[int] = Field(50, ge=1, le=1000, description="Maximum results to return")
    offset: int = Field(0, ge=0, description="Number of results to skip")


class CapabilitySearchResponse(BaseModel):
    """Response model for capability search results."""
    
    total: int = Field(..., description="Total number of matching capabilities")
    capabilities: List[ServerCapability] = Field(..., description="Matching capabilities")
    servers: Dict[str, str] = Field(..., description="Server ID to name mapping")


class ServerWithCapabilities(ServerResponse):
    """Extended server model that includes capability information."""
    
    capabilities_count: int = Field(0, description="Total number of capabilities")
    tools_count: int = Field(0, description="Number of tools")
    resources_count: int = Field(0, description="Number of resources")
    prompts_count: int = Field(0, description="Number of prompts")
    resource_templates_count: int = Field(0, description="Number of resource templates")
    last_discovery: Optional[datetime] = Field(None, description="Last capability discovery timestamp")
    discovery_status: Optional[str] = Field(None, description="Last discovery status")


# Database Models for Capabilities

class CapabilityModel:
    """Database model for server capabilities."""
    
    def __init__(
        self,
        id: int = None,
        server_id: str = None,
        type: str = None,
        name: str = None,
        description: str = None,
        input_schema: str = None,  # JSON string
        output_schema: str = None,  # JSON string
        uri_template: str = None,
        discovered_at: datetime = None,
    ):
        self.id = id
        self.server_id = server_id
        self.type = type
        self.name = name
        self.description = description
        self.input_schema = input_schema or "{}"
        self.output_schema = output_schema or "{}"
        self.uri_template = uri_template
        self.discovered_at = discovered_at or datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "server_id": self.server_id,
            "type": self.type,
            "name": self.name,
            "description": self.description,
            "input_schema": json.loads(self.input_schema) if self.input_schema else {},
            "output_schema": json.loads(self.output_schema) if self.output_schema else {},
            "uri_template": self.uri_template,
            "discovered_at": self.discovered_at,
        }


class DiscoveryModel:
    """Database model for capability discovery attempts."""
    
    def __init__(
        self,
        id: int = None,
        server_id: str = None,
        status: str = None,
        capabilities_found: int = 0,
        error_message: str = None,
        discovery_time_ms: int = None,
        discovered_at: datetime = None,
    ):
        self.id = id
        self.server_id = server_id
        self.status = status
        self.capabilities_found = capabilities_found
        self.error_message = error_message
        self.discovery_time_ms = discovery_time_ms
        self.discovered_at = discovered_at or datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "server_id": self.server_id,
            "status": self.status,
            "capabilities_found": self.capabilities_found,
            "error_message": self.error_message,
            "discovery_time_ms": self.discovery_time_ms,
            "discovered_at": self.discovered_at,
        }