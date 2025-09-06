"""
Custom exceptions for MCP Registry.

Provides specific exception types for better error handling and API responses.
"""

from typing import Optional, Any, Dict


class MCPRegistryError(Exception):
    """Base exception for MCP Registry errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ServerNotFoundError(MCPRegistryError):
    """Raised when a server is not found."""
    
    def __init__(self, server_id: str):
        super().__init__(
            message=f"Server with ID '{server_id}' not found",
            error_code="SERVER_NOT_FOUND",
            details={"server_id": server_id}
        )


class ServerAlreadyExistsError(MCPRegistryError):
    """Raised when trying to register a server that already exists."""
    
    def __init__(self, url: str, existing_id: str):
        super().__init__(
            message=f"Server with URL '{url}' already registered with ID '{existing_id}'",
            error_code="SERVER_ALREADY_EXISTS",
            details={"url": url, "existing_id": existing_id}
        )


class CapabilityDiscoveryError(MCPRegistryError):
    """Raised when capability discovery fails."""
    
    def __init__(self, server_id: str, reason: str):
        super().__init__(
            message=f"Capability discovery failed for server '{server_id}': {reason}",
            error_code="DISCOVERY_FAILED",
            details={"server_id": server_id, "reason": reason}
        )


class DatabaseError(MCPRegistryError):
    """Raised when database operations fail."""
    
    def __init__(self, operation: str, reason: str):
        super().__init__(
            message=f"Database operation '{operation}' failed: {reason}",
            error_code="DATABASE_ERROR",
            details={"operation": operation, "reason": reason}
        )


class ValidationError(MCPRegistryError):
    """Raised when data validation fails."""
    
    def __init__(self, field: str, value: Any, reason: str):
        super().__init__(
            message=f"Validation failed for field '{field}': {reason}",
            error_code="VALIDATION_ERROR",
            details={"field": field, "value": value, "reason": reason}
        )