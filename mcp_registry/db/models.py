"""
SQLAlchemy database models.
"""

from datetime import datetime, UTC
from typing import Dict, Any
from sqlalchemy import String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class Server(Base):
    """Server database model."""
    
    __tablename__ = "servers"
    
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    tags: Mapped[str] = mapped_column(Text, default="[]")  # JSON string
    transport: Mapped[str] = mapped_column(String(50), default="auto")
    status: Mapped[str] = mapped_column(String(50), default="unknown")
    server_metadata: Mapped[str] = mapped_column("metadata", Text, default="{}")  # JSON string
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    
    # Relationships
    capabilities: Mapped[list["Capability"]] = relationship("Capability", back_populates="server")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        import json
        
        # Parse JSON strings back to objects
        tags = json.loads(self.tags) if self.tags else []
        metadata = json.loads(self.server_metadata) if self.server_metadata else {}
        
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.name,  # Add display_name field using name
            "description": self.description,
            "url": self.url,
            "tags": tags,  # Parsed list
            "transport": self.transport,
            "status": self.status,
            "metadata": metadata,  # Parsed dict
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Capability(Base):
    """Capability database model."""
    
    __tablename__ = "capabilities"
    
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    server_id: Mapped[str] = mapped_column(String(255), ForeignKey("servers.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    schema: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    capability_metadata: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    
    # Relationships
    server: Mapped["Server"] = relationship("Server", back_populates="capabilities")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "server_id": self.server_id,
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "schema": self.schema,
            "metadata": self.capability_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }