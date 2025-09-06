"""
Data models for MCP Registry.

Clean Pydantic models for API requests, responses, and data validation.
"""

from .base import BaseModel, TimestampedModel
from .server import (
    ServerCreate, 
    ServerUpdate, 
    ServerResponse, 
    ServerWithCapabilities,
    ServerStatus,
    TransportType
)
from .capability import (
    CapabilityType,
    CapabilityResponse,
    CapabilityDiscoveryRequest,
    CapabilityDiscoveryResponse,
    CapabilitySearchRequest,
    CapabilitySearchResponse
)

__all__ = [
    # Base models
    "BaseModel",
    "TimestampedModel",
    
    # Server models
    "ServerCreate",
    "ServerUpdate", 
    "ServerResponse",
    "ServerWithCapabilities",
    "ServerStatus",
    "TransportType",
    
    # Capability models
    "CapabilityType",
    "CapabilityResponse",
    "CapabilityDiscoveryRequest",
    "CapabilityDiscoveryResponse", 
    "CapabilitySearchRequest",
    "CapabilitySearchResponse",
]