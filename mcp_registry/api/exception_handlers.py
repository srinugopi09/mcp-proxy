"""
Centralized exception handlers for the MCP Registry API.

This module contains all FastAPI exception handlers to ensure consistent
error responses across the entire API. Each handler converts domain exceptions
into appropriate HTTP responses with standardized error formats.
"""

import uuid
from datetime import datetime, UTC
from typing import Dict, Any, Optional
from fastapi import Request
from fastapi.responses import JSONResponse
import logging

from ..core.exceptions import (
    ServerNotFoundError, 
    CapabilityDiscoveryError, 
    ValidationError,
    DatabaseError
)

logger = logging.getLogger(__name__)


def create_error_response(
    error_code: str,
    message: str,
    status_code: int,
    request_path: str,
    request_id: Optional[str] = None,
    details: Dict[str, Any] = None
) -> JSONResponse:
    """
    Create a standardized error response.
    
    Args:
        error_code: Machine-readable error code
        message: Human-readable error message
        status_code: HTTP status code
        request_path: The request path that caused the error
        request_id: Optional request ID for tracing
        details: Optional additional error details
    
    Returns:
        JSONResponse with standardized error format
    """
    content = {
        "error": error_code,
        "message": message,
        "timestamp": datetime.now(UTC).isoformat(),
        "path": request_path,
        "request_id": request_id or str(uuid.uuid4())
    }
    
    if details:
        content["details"] = details
    
    return JSONResponse(status_code=status_code, content=content)


def get_request_id(request: Request) -> str:
    """
    Extract or generate request ID for tracing.
    
    Looks for request ID in headers (X-Request-ID, X-Correlation-ID) 
    or generates a new UUID if not found.
    """
    # Check common request ID headers
    request_id = (
        request.headers.get("x-request-id") or
        request.headers.get("x-correlation-id") or
        request.headers.get("request-id") or
        str(uuid.uuid4())
    )
    return request_id


async def server_not_found_handler(request: Request, exc: ServerNotFoundError) -> JSONResponse:
    """Handle ServerNotFoundError exceptions."""
    request_id = get_request_id(request)
    
    logger.warning(
        f"Server not found - Request ID: {request_id}, Path: {request.url.path}, "
        f"Details: {getattr(exc, 'details', {})}"
    )
    
    return create_error_response(
        error_code="SERVER_NOT_FOUND",
        message=str(exc),
        status_code=404,
        request_path=str(request.url.path),
        request_id=request_id,
        details=getattr(exc, 'details', None)
    )


async def capability_discovery_error_handler(request: Request, exc: CapabilityDiscoveryError) -> JSONResponse:
    """Handle CapabilityDiscoveryError exceptions."""
    request_id = get_request_id(request)
    
    logger.error(
        f"Capability discovery failed - Request ID: {request_id}, Path: {request.url.path}, "
        f"Error: {exc}, Details: {getattr(exc, 'details', {})}"
    )
    
    return create_error_response(
        error_code="DISCOVERY_FAILED",
        message=str(exc),
        status_code=503,  # Service Unavailable
        request_path=str(request.url.path),
        request_id=request_id,
        details=getattr(exc, 'details', None)
    )


async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle ValidationError exceptions."""
    request_id = get_request_id(request)
    
    logger.warning(
        f"Validation error - Request ID: {request_id}, Path: {request.url.path}, "
        f"Error: {exc}, Details: {getattr(exc, 'details', {})}"
    )
    
    return create_error_response(
        error_code="VALIDATION_ERROR",
        message=str(exc),
        status_code=400,
        request_path=str(request.url.path),
        request_id=request_id,
        details=getattr(exc, 'details', None)
    )


async def database_error_handler(request: Request, exc: DatabaseError) -> JSONResponse:
    """Handle DatabaseError exceptions."""
    request_id = get_request_id(request)
    
    # Log database errors for debugging but don't expose details to client
    logger.error(
        f"Database error - Request ID: {request_id}, Path: {request.url.path}, "
        f"Error: {exc}", exc_info=True
    )
    
    return create_error_response(
        error_code="DATABASE_ERROR",
        message="A database error occurred",
        status_code=500,
        request_path=str(request.url.path),
        request_id=request_id
    )


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle ValueError exceptions (typically validation issues)."""
    request_id = get_request_id(request)
    
    logger.warning(
        f"Value error - Request ID: {request_id}, Path: {request.url.path}, "
        f"Error: {exc}"
    )
    
    return create_error_response(
        error_code="INVALID_INPUT",
        message=str(exc),
        status_code=400,
        request_path=str(request.url.path),
        request_id=request_id
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions.
    
    This is the catch-all handler for any unhandled exceptions.
    It logs the full error for debugging but returns a generic message to the client.
    """
    request_id = get_request_id(request)
    
    logger.error(
        f"Unexpected error - Request ID: {request_id}, Path: {request.url.path}, "
        f"Error: {exc}", exc_info=True
    )
    
    return create_error_response(
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred",
        status_code=500,
        request_path=str(request.url.path),
        request_id=request_id
    )


def register_exception_handlers(app) -> None:
    """
    Register all exception handlers with the FastAPI application.
    
    This function should be called during app initialization to register
    all custom exception handlers. The order matters - more specific
    exceptions should be registered before more general ones.
    
    Args:
        app: FastAPI application instance
    """
    # Register specific domain exceptions first
    app.add_exception_handler(ServerNotFoundError, server_not_found_handler)
    app.add_exception_handler(CapabilityDiscoveryError, capability_discovery_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(DatabaseError, database_error_handler)
    
    # Register general Python exceptions
    app.add_exception_handler(ValueError, value_error_handler)
    
    # Register catch-all handler last
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Exception handlers registered successfully")