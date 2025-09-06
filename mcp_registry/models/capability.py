"""
Capability models for MCP Registry.

Pydantic models for capability discovery, search, and responses.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field

from .base import BaseModel, TimestampedModel


class CapabilityType(str, Enum):
    """MCP capability types."""
    TOOL = "tool"
    RESOURCE = "resource"
    PROMPT = "prompt"
    RESOURCE_TEMPLATE = "resource_template"


class CapabilityResponse(TimestampedModel):
    """Model for a discovered server capability."""
    
    id: Optional[int] = Field(
        default=None,
        description="Database ID"
    )
    server_id: str = Field(
        description="Server ID this capability belongs to",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    type: CapabilityType = Field(
        description="Capability type"
    )
    name: str = Field(
        description="Capability name",
        examples=["get_weather", "weather_forecast"]
    )
    description: Optional[str] = Field(
        default=None,
        description="Capability description",
        examples=["Get current weather for a location"]
    )
    input_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Input schema (JSON Schema)"
    )
    output_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Output schema (JSON Schema)"
    )
    uri_template: Optional[str] = Field(
        default=None,
        description="URI template for resource templates",
        examples=["weather://location/{location_id}"]
    )
    discovered_at: datetime = Field(
        description="Discovery timestamp"
    )


class CapabilityDiscoveryRequest(BaseModel):
    """Request model for triggering capability discovery."""
    
    force_refresh: bool = Field(
        default=False,
        description="Force refresh even if recently discovered"
    )
    timeout_seconds: Optional[int] = Field(
        default=30,
        description="Discovery timeout in seconds",
        ge=1,
        le=300
    )


class CapabilityDiscoveryResponse(BaseModel):
    """Response model for capability discovery results."""
    
    server_id: str = Field(
        description="Server ID",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    status: str = Field(
        description="Discovery status",
        examples=["success", "failed", "partial", "cached"]
    )
    capabilities_found: int = Field(
        description="Number of capabilities discovered",
        ge=0
    )
    discovery_time_ms: int = Field(
        description="Discovery time in milliseconds",
        ge=0
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if failed"
    )
    capabilities: List[CapabilityResponse] = Field(
        default_factory=list,
        description="Discovered capabilities"
    )
    
    # Enhanced server information (optional, populated if discovered)
    server_info: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Server-introspected information"
    )
    server_name: Optional[str] = Field(
        default=None,
        description="Server's self-reported name"
    )
    server_version: Optional[str] = Field(
        default=None,
        description="Server version"
    )
    protocol_version: Optional[str] = Field(
        default=None,
        description="MCP protocol version"
    )
    server_capabilities: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Server capability flags"
    )
    response_time_ms: Optional[int] = Field(
        default=None,
        description="Server response time in milliseconds",
        ge=0
    )


class CapabilitySearchRequest(BaseModel):
    """Request model for searching capabilities."""
    
    query: Optional[str] = Field(
        default=None,
        description="Search query",
        examples=["weather"]
    )
    type: Optional[CapabilityType] = Field(
        default=None,
        description="Filter by capability type"
    )
    server_id: Optional[str] = Field(
        default=None,
        description="Filter by server ID"
    )
    limit: Optional[int] = Field(
        default=50,
        description="Maximum results to return",
        ge=1,
        le=1000
    )
    offset: int = Field(
        default=0,
        description="Number of results to skip",
        ge=0
    )


class CapabilitySearchResponse(BaseModel):
    """Response model for capability search results."""
    
    total: int = Field(
        description="Total number of matching capabilities",
        ge=0
    )
    capabilities: List[CapabilityResponse] = Field(
        description="Matching capabilities"
    )
    servers: Dict[str, str] = Field(
        description="Server ID to name mapping"
    )
    query_time_ms: Optional[int] = Field(
        default=None,
        description="Search query time in milliseconds",
        ge=0
    )