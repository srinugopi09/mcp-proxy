"""
MCP Server Registry

A registry system for managing and discovering MCP servers.
Provides database operations, API endpoints, and health monitoring.
"""

from .models import (
    ServerModel, ServerCreate, ServerUpdate, ServerResponse,
    ServerCapability, CapabilityDiscoveryRequest, CapabilityDiscoveryResponse,
    CapabilitySearchRequest, CapabilitySearchResponse, ServerWithCapabilities
)
from .database import Database, get_database
from .api import create_registry_app
from .capability_discovery import CapabilityDiscoveryService

__all__ = [
    "ServerModel",
    "ServerCreate", 
    "ServerUpdate",
    "ServerResponse",
    "ServerCapability",
    "CapabilityDiscoveryRequest",
    "CapabilityDiscoveryResponse", 
    "CapabilitySearchRequest",
    "CapabilitySearchResponse",
    "ServerWithCapabilities",
    "Database",
    "get_database",
    "create_registry_app",
    "CapabilityDiscoveryService",
]