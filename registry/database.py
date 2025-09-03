"""
SQLite database operations for MCP server registry.

Handles database initialization, CRUD operations, and connection management.
"""

import os
import sqlite3
import threading
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from .models import ServerModel, ServerCreate, ServerUpdate


class Database:
    """SQLite database manager for MCP server registry."""
    
    def __init__(self, db_path: str = None):
        """Initialize database with optional custom path."""
        if db_path is None:
            db_path = os.environ.get('MCP_REGISTRY_DB', './mcp_registry.db')
        
        self.db_path = db_path
        self._local = threading.local()
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    @contextmanager
    def _get_cursor(self):
        """Context manager for database operations."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
    
    def _init_database(self) -> None:
        """Initialize database tables."""
        with self._get_cursor() as cursor:
            # Create servers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS servers (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE,
                    description TEXT,
                    tags TEXT DEFAULT '[]',
                    transport TEXT DEFAULT 'auto',
                    status TEXT DEFAULT 'unknown',
                    metadata TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_checked TIMESTAMP
                )
            """)
            
            # Create indexes for better query performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_servers_status ON servers(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_servers_transport ON servers(transport)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_servers_created_at ON servers(created_at)")
    
    def create_server(self, server_data: ServerCreate) -> ServerModel:
        """Create a new server registration."""
        server = ServerModel.from_create(server_data)
        
        with self._get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO servers (
                    id, name, url, description, tags, transport, 
                    status, metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                server.id, server.name, server.url, server.description,
                server.tags, server.transport, server.status, server.metadata,
                server.created_at, server.updated_at
            ))
        
        return server
    
    def get_server(self, server_id: str) -> Optional[ServerModel]:
        """Get server by ID."""
        with self._get_cursor() as cursor:
            cursor.execute("SELECT * FROM servers WHERE id = ?", (server_id,))
            row = cursor.fetchone()
            
            if row:
                return ServerModel(
                    id=row['id'],
                    name=row['name'],
                    url=row['url'],
                    description=row['description'],
                    tags=row['tags'],
                    transport=row['transport'],
                    status=row['status'],
                    metadata=row['metadata'],
                    created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')) if row['created_at'] else None,
                    updated_at=datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00')) if row['updated_at'] else None,
                    last_checked=datetime.fromisoformat(row['last_checked'].replace('Z', '+00:00')) if row['last_checked'] else None,
                )
            return None
    
    def get_server_by_url(self, url: str) -> Optional[ServerModel]:
        """Get server by URL."""
        with self._get_cursor() as cursor:
            cursor.execute("SELECT * FROM servers WHERE url = ?", (url,))
            row = cursor.fetchone()
            
            if row:
                return ServerModel(
                    id=row['id'],
                    name=row['name'],
                    url=row['url'],
                    description=row['description'],
                    tags=row['tags'],
                    transport=row['transport'],
                    status=row['status'],
                    metadata=row['metadata'],
                    created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')) if row['created_at'] else None,
                    updated_at=datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00')) if row['updated_at'] else None,
                    last_checked=datetime.fromisoformat(row['last_checked'].replace('Z', '+00:00')) if row['last_checked'] else None,
                )
            return None
    
    def list_servers(
        self, 
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[ServerModel]:
        """List servers with optional filtering."""
        query = "SELECT * FROM servers"
        params = []
        conditions = []
        
        if status:
            conditions.append("status = ?")
            params.append(status)
        
        if tags:
            # Simple tag filtering - check if any of the provided tags exist in the server's tags
            tag_conditions = []
            for tag in tags:
                tag_conditions.append("tags LIKE ?")
                params.append(f'%"{tag}"%')
            if tag_conditions:
                conditions.append(f"({' OR '.join(tag_conditions)})")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY created_at DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
            if offset:
                query += " OFFSET ?"
                params.append(offset)
        
        servers = []
        with self._get_cursor() as cursor:
            cursor.execute(query, params)
            for row in cursor.fetchall():
                servers.append(ServerModel(
                    id=row['id'],
                    name=row['name'],
                    url=row['url'],
                    description=row['description'],
                    tags=row['tags'],
                    transport=row['transport'],
                    status=row['status'],
                    metadata=row['metadata'],
                    created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')) if row['created_at'] else None,
                    updated_at=datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00')) if row['updated_at'] else None,
                    last_checked=datetime.fromisoformat(row['last_checked'].replace('Z', '+00:00')) if row['last_checked'] else None,
                ))
        
        return servers
    
    def update_server(self, server_id: str, server_data: ServerUpdate) -> Optional[ServerModel]:
        """Update an existing server."""
        server = self.get_server(server_id)
        if not server:
            return None
        
        server.update_from_data(server_data)
        
        with self._get_cursor() as cursor:
            cursor.execute("""
                UPDATE servers SET 
                    name = ?, url = ?, description = ?, tags = ?, 
                    transport = ?, metadata = ?, updated_at = ?
                WHERE id = ?
            """, (
                server.name, server.url, server.description, server.tags,
                server.transport, server.metadata, server.updated_at, server_id
            ))
        
        return server
    
    def delete_server(self, server_id: str) -> bool:
        """Delete a server registration."""
        with self._get_cursor() as cursor:
            cursor.execute("DELETE FROM servers WHERE id = ?", (server_id,))
            return cursor.rowcount > 0
    
    def update_server_status(self, server_id: str, status: str, last_checked: datetime = None) -> bool:
        """Update server health status."""
        if last_checked is None:
            last_checked = datetime.utcnow()
        
        with self._get_cursor() as cursor:
            cursor.execute("""
                UPDATE servers SET status = ?, last_checked = ?, updated_at = ?
                WHERE id = ?
            """, (status, last_checked, datetime.utcnow(), server_id))
            return cursor.rowcount > 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        with self._get_cursor() as cursor:
            # Total servers
            cursor.execute("SELECT COUNT(*) as total FROM servers")
            total = cursor.fetchone()['total']
            
            # Status breakdown
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM servers 
                GROUP BY status
            """)
            status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
            
            # Transport breakdown
            cursor.execute("""
                SELECT transport, COUNT(*) as count 
                FROM servers 
                GROUP BY transport
            """)
            transport_counts = {row['transport']: row['count'] for row in cursor.fetchall()}
            
            return {
                "total_servers": total,
                "status_breakdown": status_counts,
                "transport_breakdown": transport_counts,
            }
    
    def close(self) -> None:
        """Close database connections."""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()


# Global database instance
_database: Optional[Database] = None
_database_lock = threading.Lock()


def get_database(db_path: str = None) -> Database:
    """Get or create global database instance."""
    global _database
    
    with _database_lock:
        if _database is None:
            _database = Database(db_path)
        return _database