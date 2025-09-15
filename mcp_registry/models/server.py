"""
Server models for MCP Registry.

Pydantic models for server registration, updates, and responses.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field, HttpUrl, field_validator

from .base import BaseModel, TimestampedModel


class TransportType(str, Enum):
    """MCP transport types."""
    AUTO = "auto"
    HTTP = "http"
    SSE = "sse"
    STDIO = "stdio"


class ServerStatus(str, Enum):
    """Server health status."""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    ERROR = "error"


class ServerCreate(BaseModel):
    """Model for creating a new server."""
    
    name: str = Field(
        min_length=1,
        max_length=255,
        description="Human-readable server name",
        examples=["Weather Forecast API"]
    )
    url: HttpUrl = Field(
        description="MCP server endpoint URL",
        examples=["http://weather-api.company.com/mcp"]
    )
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Server description",
        examples=["Provides weather forecasting capabilities"]
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Categorization tags",
        examples=[["weather", "forecast", "production"]]
    )
    transport: TransportType = Field(
        default=TransportType.AUTO,
        description="Transport type for MCP communication"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional server metadata"
    )
    
    @field_validator('url')
    @classmethod
    def validate_mcp_url(cls, v: HttpUrl) -> HttpUrl:
        """Validate that URL ends with /mcp."""
        if not str(v).endswith('/mcp'):
            raise ValueError('URL must end with /mcp')
        return v
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Validate and clean tags."""
        if len(v) > 20:
            raise ValueError('Maximum 20 tags allowed')
        
        cleaned_tags = []
        for tag in v:
            tag = tag.strip().lower()
            if tag and len(tag) <= 50:
                cleaned_tags.append(tag)
        
        return list(set(cleaned_tags))  # Remove duplicates


class ServerUpdate(BaseModel):
    """Model for updating an existing server."""
    
    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Human-readable server name"
    )
    url: Optional[HttpUrl] = Field(
        default=None,
        description="MCP server endpoint URL"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Server description"
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="Categorization tags"
    )
    transport: Optional[TransportType] = Field(
        default=None,
        description="Transport type for MCP communication"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional server metadata"
    )
    
    @field_validator('url')
    @classmethod
    def validate_mcp_url(cls, v: Optional[HttpUrl]) -> Optional[HttpUrl]:
        """Validate that URL ends with /mcp."""
        if v is not None and not str(v).endswith('/mcp'):
            raise ValueError('URL must end with /mcp')
        return v
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate and clean tags."""
        if v is None:
            return v
        
        if len(v) > 20:
            raise ValueError('Maximum 20 tags allowed')
        
        cleaned_tags = []
        for tag in v:
            tag = tag.strip().lower()
            if tag and len(tag) <= 50:
                cleaned_tags.append(tag)
        
        return list(set(cleaned_tags))  # Remove duplicates


class ServerResponse(TimestampedModel):
    """Model for server data in API responses."""
    
    id: str = Field(
        description="Auto-generated server ID",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    name: str = Field(
        description="Human-readable server name (display name)",
        examples=["Weather Forecast API"]
    )
    display_name: Optional[str] = Field(
        default=None,
        description="User-provided display name",
        examples=["Weather Forecast API"]
    )
    url: str = Field(
        description="MCP server URL",
        examples=["http://weather-api.company.com/mcp"]
    )
    description: Optional[str] = Field(
        default=None,
        description="Server description"
    )
    tags: List[str] = Field(
        description="Categorization tags",
        examples=[["weather", "forecast"]]
    )
    transport: TransportType = Field(
        description="Transport type"
    )
    status: ServerStatus = Field(
        description="Server health status"
    )
    metadata: Dict[str, Any] = Field(
        description="Additional metadata"
    )
    last_checked: Optional[datetime] = Field(
        default=None,
        description="Last health check timestamp"
    )
    
    # Server-introspected information (optional)
    server_name: Optional[str] = Field(
        default=None,
        description="Server's self-reported name",
        examples=["weather-mcp-server"]
    )
    server_version: Optional[str] = Field(
        default=None,
        description="Server version",
        examples=["1.2.3"]
    )
    protocol_version: Optional[str] = Field(
        default=None,
        description="MCP protocol version",
        examples=["2024-11-05"]
    )
    server_capabilities: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Server capability flags"
    )
    implementation_info: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Implementation details"
    )
    
    # Performance and health metrics (optional)
    last_ping_time: Optional[datetime] = Field(
        default=None,
        description="Last successful ping"
    )
    avg_response_time_ms: Optional[int] = Field(
        default=None,
        description="Average response time in milliseconds",
        ge=0
    )
    total_discoveries: Optional[int] = Field(
        default=None,
        description="Total discovery attempts",
        ge=0
    )
    successful_discoveries: Optional[int] = Field(
        default=None,
        description="Successful discovery attempts",
        ge=0
    )
    discovery_success_rate: Optional[float] = Field(
        default=None,
        description="Discovery success rate (0.0-1.0)",
        ge=0.0,
        le=1.0
    )


class ServerWithCapabilities(ServerResponse):
    """Extended server model that includes capability information."""
    
    capabilities_count: int = Field(
        default=0,
        description="Total number of capabilities",
        ge=0
    )
    tools_count: int = Field(
        default=0,
        description="Number of tools",
        ge=0
    )
    resources_count: int = Field(
        default=0,
        description="Number of resources",
        ge=0
    )
    prompts_count: int = Field(
        default=0,
        description="Number of prompts",
        ge=0
    )
    resource_templates_count: int = Field(
        default=0,
        description="Number of resource templates",
        ge=0
    )
    last_discovery: Optional[datetime] = Field(
        default=None,
        description="Last capability discovery timestamp"
    )
    discovery_status: Optional[str] = Field(
        default=None,
        description="Last discovery status",
        examples=["success", "failed", "partial"]
    )