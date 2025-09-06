"""
MCP Registry - Enterprise Model Context Protocol Server Registry

A comprehensive platform for managing, discovering, and proxying MCP servers
with advanced features like capability discovery, performance monitoring,
and extensible plugin architecture.
"""

__version__ = "2.0.0"
__author__ = "MCP Registry Contributors"

# Public API exports
from .core.config import Settings, get_settings
from .api.app import create_app
from .services.registry import RegistryService
from .services.discovery import DiscoveryService
from .services.proxy import ProxyService
from .models.server import ServerCreate, ServerUpdate, ServerResponse
from .models.capability import CapabilityResponse, CapabilitySearchRequest

__all__ = [
    # Core
    "Settings",
    "get_settings",
    "create_app",
    
    # Services
    "RegistryService", 
    "DiscoveryService",
    "ProxyService",
    
    # Models
    "ServerCreate",
    "ServerUpdate", 
    "ServerResponse",
    "CapabilityResponse",
    "CapabilitySearchRequest",
]