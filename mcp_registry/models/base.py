"""
Base models for MCP Registry.

Provides common functionality and patterns for all models.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel as PydanticBaseModel, Field, ConfigDict


class BaseModel(PydanticBaseModel):
    """Base model with common configuration."""
    
    model_config = ConfigDict(
        # Enable ORM mode for SQLAlchemy integration
        from_attributes=True,
        # Use enum values instead of enum objects
        use_enum_values=True,
        # Validate assignment
        validate_assignment=True,
        # Allow population by field name or alias
        populate_by_name=True,
        # JSON schema extra
        json_schema_extra={
            "examples": []
        }
    )


class TimestampedModel(BaseModel):
    """Base model with timestamp fields."""
    
    created_at: datetime = Field(
        description="Creation timestamp",
        examples=["2024-01-01T00:00:00Z"]
    )
    updated_at: datetime = Field(
        description="Last update timestamp", 
        examples=["2024-01-01T00:00:00Z"]
    )


class PaginatedResponse(BaseModel):
    """Base model for paginated responses."""
    
    total: int = Field(
        description="Total number of items",
        ge=0,
        examples=[100]
    )
    page: int = Field(
        description="Current page number",
        ge=1,
        examples=[1]
    )
    size: int = Field(
        description="Items per page",
        ge=1,
        le=1000,
        examples=[20]
    )
    pages: int = Field(
        description="Total number of pages",
        ge=1,
        examples=[5]
    )


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(
        description="Service health status",
        examples=["healthy"]
    )
    service: str = Field(
        description="Service name",
        examples=["mcp-registry"]
    )
    version: str = Field(
        description="Service version",
        examples=["2.0.0"]
    )
    timestamp: datetime = Field(
        description="Health check timestamp",
        examples=["2024-01-01T00:00:00Z"]
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional health details"
    )


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error: str = Field(
        description="Error code",
        examples=["SERVER_NOT_FOUND"]
    )
    message: str = Field(
        description="Human-readable error message",
        examples=["Server with ID 'abc123' not found"]
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )
    timestamp: datetime = Field(
        description="Error timestamp",
        examples=["2024-01-01T00:00:00Z"]
    )