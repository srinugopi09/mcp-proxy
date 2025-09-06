"""
SQLAlchemy database models.
"""

from datetime import datetime
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    capabilities: Mapped[list["Capability"]] = relationship("Capability", back_populates="server")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "tags": self.tags,
            "transport": self.transport,
            "status": self.status,
            "metadata": self.server_metadata,
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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