"""
SQLAlchemy ORM models for MCP Registry.

Database models with relationships and constraints.
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    Boolean, DateTime, Integer, String, Text, JSON, 
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Server(Base):
    """Server ORM model."""
    
    __tablename__ = "servers"
    
    # Basic server information
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[str] = mapped_column(Text, default="[]")  # JSON string
    transport: Mapped[str] = mapped_column(String(50), default="auto")
    status: Mapped[str] = mapped_column(String(50), default="unknown")
    server_metadata: Mapped[str] = mapped_column("metadata", Text, default="{}")  # JSON string
    last_checked: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Server-introspected information
    server_name: Mapped[Optional[str]] = mapped_column(String(255))
    server_version: Mapped[Optional[str]] = mapped_column(String(100))
    protocol_version: Mapped[Optional[str]] = mapped_column(String(50))
    server_capabilities: Mapped[str] = mapped_column(Text, default="{}")  # JSON string
    implementation_info: Mapped[str] = mapped_column(Text, default="{}")  # JSON string
    
    # Performance and health metrics
    last_ping_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    avg_response_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    total_discoveries: Mapped[int] = mapped_column(Integer, default=0)
    successful_discoveries: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships
    capabilities: Mapped[List["Capability"]] = relationship(
        "Capability", 
        back_populates="server",
        cascade="all, delete-orphan"
    )
    discoveries: Mapped[List["CapabilityDiscovery"]] = relationship(
        "CapabilityDiscovery",
        back_populates="server", 
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_servers_status", "status"),
        Index("idx_servers_transport", "transport"),
        Index("idx_servers_created_at", "created_at"),
        Index("idx_servers_url", "url"),
    )
    
    def __repr__(self) -> str:
        return f"<Server(id='{self.id}', name='{self.name}', url='{self.url}')>"


class Capability(Base):
    """Capability ORM model."""
    
    __tablename__ = "capabilities"
    
    # Foreign key to server
    server_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("servers.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Capability information
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    input_schema: Mapped[str] = mapped_column(Text, default="{}")  # JSON string
    output_schema: Mapped[str] = mapped_column(Text, default="{}")  # JSON string
    uri_template: Mapped[Optional[str]] = mapped_column(String(500))
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    
    # Relationships
    server: Mapped["Server"] = relationship("Server", back_populates="capabilities")
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("server_id", "type", "name", name="uq_server_capability"),
        Index("idx_capabilities_server_id", "server_id"),
        Index("idx_capabilities_type", "type"),
        Index("idx_capabilities_name", "name"),
        Index("idx_capabilities_discovered_at", "discovered_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Capability(id='{self.id}', name='{self.name}', type='{self.type}')>"


class CapabilityDiscovery(Base):
    """Capability discovery attempt ORM model."""
    
    __tablename__ = "capability_discoveries"
    
    # Foreign key to server
    server_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("servers.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Discovery information
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    capabilities_found: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    discovery_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    
    # Relationships
    server: Mapped["Server"] = relationship("Server", back_populates="discoveries")
    
    # Indexes
    __table_args__ = (
        Index("idx_discoveries_server_id", "server_id"),
        Index("idx_discoveries_status", "status"),
        Index("idx_discoveries_discovered_at", "discovered_at"),
    )
    
    def __repr__(self) -> str:
        return f"<CapabilityDiscovery(id='{self.id}', server_id='{self.server_id}', status='{self.status}')>"