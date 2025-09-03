"""
Pydantic models for MCP server registry.

Defines the data structures for server registration, updates, and responses.
"""

import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
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