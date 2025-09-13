"""Pydantic models for request/response bodies."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, HttpUrl


class CreateSessionRequest(BaseModel):
    """Request body for creating a new server connection."""

    remote_url: HttpUrl = Field(
        ..., 
        description="Base URL of the remote MCP server (must include path to /mcp)"
    )
    token: Optional[str] = Field(
        None,
        description=(
            "Bearer token for Authorization header. If provided this will be used "
            "to set `Authorization: Bearer <token>` on all requests to the remote server. "
            "You may alternatively specify custom headers via the `headers` field."
        ),
    )
    headers: Optional[Dict[str, str]] = Field(
        None,
        description=(
            "Arbitrary HTTP headers to inject into requests to the remote server. "
            "If an `Authorization` header is present it overrides the `token` field."
        ),
    )


class CreateSessionResponse(BaseModel):
    """Response body for server connection creation."""

    session_id: str  # Keep as session_id for backward compatibility
    prefix: str
    remote_url: HttpUrl
    expires_at: datetime


class ToolCallRequest(BaseModel):
    """Request body for calling a tool."""

    arguments: Dict[str, Any] = Field(
        ..., 
        description="Arguments to pass to the tool. Must match the tool's schema."
    )
    stream: Optional[bool] = Field(
        False,
        description=(
            "When true the response will be streamed back to the client as NDJSON. "
            "If false (default) the full result is returned once the tool completes."
        ),
    )


class ToolCallResponse(BaseModel):
    """Response body for non-streaming tool calls."""

    content: Optional[Any] = None
    structured_content: Optional[Any] = None


class SessionRefreshResponse(BaseModel):
    """Response body for server connection refresh."""
    
    detail: str
    session_id: str  # Keep as session_id for backward compatibility
    new_expires_at: datetime


class SessionCloseResponse(BaseModel):
    """Response body for server connection closure."""
    
    detail: str
    session_id: str  # Keep as session_id for backward compatibility


class PingResponse(BaseModel):
    """Response body for ping endpoint."""
    
    detail: str = "pong"
    session_id: str  # Keep as session_id for backward compatibility


class ToolInfo(BaseModel):
    """Information about a tool available on the remote server."""
    
    name: str
    description: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    returns: Optional[Dict[str, Any]] = None
    structured: bool = False


class ToolsListResponse(BaseModel):
    """Response body for listing tools."""
    
    tools: list[ToolInfo]
    session_id: str  # Keep as session_id for backward compatibility


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)