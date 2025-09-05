"""
SQLite database operations for MCP server registry.

Handles database initialization, CRUD operations, and connection management.
"""

import json
import os
import sqlite3
import threading
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from .models import ServerModel, ServerCreate, ServerUpdate, CapabilityModel, DiscoveryModel, ServerCapability


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
            
            # Enable foreign key constraints
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            
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
            # Create servers table with enhanced server information support
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS servers (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,  -- Will become display_name (backward compatibility)
                    url TEXT NOT NULL UNIQUE,
                    description TEXT,
                    tags TEXT DEFAULT '[]',
                    transport TEXT DEFAULT 'auto',
                    status TEXT DEFAULT 'unknown',
                    metadata TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_checked TIMESTAMP,
                    
                    -- Enhanced server information (server-introspected)
                    server_name TEXT,           -- Server's self-reported name
                    server_version TEXT,        -- Server version
                    protocol_version TEXT,      -- MCP protocol version
                    server_capabilities TEXT DEFAULT '{}',  -- JSON: server capability flags
                    implementation_info TEXT DEFAULT '{}',  -- JSON: implementation details
                    
                    -- Performance and health metrics
                    last_ping_time TIMESTAMP,
                    avg_response_time_ms INTEGER DEFAULT 0,
                    total_discoveries INTEGER DEFAULT 0,
                    successful_discoveries INTEGER DEFAULT 0
                )
            """)
            
            # Add new columns to existing tables (migration support)
            self._migrate_server_table(cursor)
            
            # Create server capabilities table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS server_capabilities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    input_schema TEXT DEFAULT '{}',
                    output_schema TEXT DEFAULT '{}',
                    uri_template TEXT,
                    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE,
                    UNIQUE(server_id, type, name)
                )
            """)
            
            # Create capability discoveries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS capability_discoveries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    capabilities_found INTEGER DEFAULT 0,
                    error_message TEXT,
                    discovery_time_ms INTEGER,
                    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes for better query performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_servers_status ON servers(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_servers_transport ON servers(transport)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_servers_created_at ON servers(created_at)")
            
            # Capability indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_capabilities_server_id ON server_capabilities(server_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_capabilities_type ON server_capabilities(type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_capabilities_name ON server_capabilities(name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_discoveries_server_id ON capability_discoveries(server_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_discoveries_status ON capability_discoveries(status)")
    
    def _migrate_server_table(self, cursor) -> None:
        """Add new columns to existing servers table for backward compatibility."""
        # Get existing columns
        cursor.execute("PRAGMA table_info(servers)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        # Add new columns if they don't exist
        new_columns = [
            ("server_name", "TEXT"),
            ("server_version", "TEXT"), 
            ("protocol_version", "TEXT"),
            ("server_capabilities", "TEXT DEFAULT '{}'"),
            ("implementation_info", "TEXT DEFAULT '{}'"),
            ("last_ping_time", "TIMESTAMP"),
            ("avg_response_time_ms", "INTEGER DEFAULT 0"),
            ("total_discoveries", "INTEGER DEFAULT 0"),
            ("successful_discoveries", "INTEGER DEFAULT 0")
        ]
        
        for column_name, column_def in new_columns:
            if column_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE servers ADD COLUMN {column_name} {column_def}")
                    print(f"Added column {column_name} to servers table")
                except Exception as e:
                    # Column might already exist in some edge cases
                    print(f"Note: Could not add column {column_name}: {e}")
    
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
                    
                    # Server-introspected information
                    server_name=row['server_name'] if 'server_name' in row.keys() else None,
                    server_version=row['server_version'] if 'server_version' in row.keys() else None,
                    protocol_version=row['protocol_version'] if 'protocol_version' in row.keys() else None,
                    server_capabilities=row['server_capabilities'] if 'server_capabilities' in row.keys() else None,
                    implementation_info=row['implementation_info'] if 'implementation_info' in row.keys() else None,
                    
                    # Performance metrics
                    last_ping_time=datetime.fromisoformat(row['last_ping_time'].replace('Z', '+00:00')) if ('last_ping_time' in row.keys() and row['last_ping_time']) else None,
                    avg_response_time_ms=row['avg_response_time_ms'] if 'avg_response_time_ms' in row.keys() else None,
                    total_discoveries=row['total_discoveries'] if 'total_discoveries' in row.keys() else None,
                    successful_discoveries=row['successful_discoveries'] if 'successful_discoveries' in row.keys() else None,
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
                    
                    # Server-introspected information
                    server_name=row['server_name'] if 'server_name' in row.keys() else None,
                    server_version=row['server_version'] if 'server_version' in row.keys() else None,
                    protocol_version=row['protocol_version'] if 'protocol_version' in row.keys() else None,
                    server_capabilities=row['server_capabilities'] if 'server_capabilities' in row.keys() else None,
                    implementation_info=row['implementation_info'] if 'implementation_info' in row.keys() else None,
                    
                    # Performance metrics
                    last_ping_time=datetime.fromisoformat(row['last_ping_time'].replace('Z', '+00:00')) if ('last_ping_time' in row.keys() and row['last_ping_time']) else None,
                    avg_response_time_ms=row['avg_response_time_ms'] if 'avg_response_time_ms' in row.keys() else None,
                    total_discoveries=row['total_discoveries'] if 'total_discoveries' in row.keys() else None,
                    successful_discoveries=row['successful_discoveries'] if 'successful_discoveries' in row.keys() else None,
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
                    updated_at=datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00')) if row['updated_at'] else None,
                    last_checked=datetime.fromisoformat(row['last_checked'].replace('Z', '+00:00')) if row['last_checked'] else None,
                    
                    # Server-introspected information
                    server_name=row['server_name'] if 'server_name' in row.keys() else None,
                    server_version=row['server_version'] if 'server_version' in row.keys() else None,
                    protocol_version=row['protocol_version'] if 'protocol_version' in row.keys() else None,
                    server_capabilities=row['server_capabilities'] if 'server_capabilities' in row.keys() else None,
                    implementation_info=row['implementation_info'] if 'implementation_info' in row.keys() else None,
                    
                    # Performance metrics
                    last_ping_time=datetime.fromisoformat(row['last_ping_time'].replace('Z', '+00:00')) if ('last_ping_time' in row.keys() and row['last_ping_time']) else None,
                    avg_response_time_ms=row['avg_response_time_ms'] if 'avg_response_time_ms' in row.keys() else None,
                    total_discoveries=row['total_discoveries'] if 'total_discoveries' in row.keys() else None,
                    successful_discoveries=row['successful_discoveries'] if 'successful_discoveries' in row.keys() else None,
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
        """Delete a server registration and all associated data."""
        with self._get_cursor() as cursor:
            # Explicitly delete associated capabilities first (backup to foreign key cascade)
            cursor.execute("DELETE FROM server_capabilities WHERE server_id = ?", (server_id,))
            capabilities_deleted = cursor.rowcount
            
            # Delete associated discovery history
            cursor.execute("DELETE FROM capability_discoveries WHERE server_id = ?", (server_id,))
            discoveries_deleted = cursor.rowcount
            
            # Delete the server itself
            cursor.execute("DELETE FROM servers WHERE id = ?", (server_id,))
            server_deleted = cursor.rowcount > 0
            
            if server_deleted and (capabilities_deleted > 0 or discoveries_deleted > 0):
                print(f"Deleted server {server_id} with {capabilities_deleted} capabilities and {discoveries_deleted} discovery records")
            
            return server_deleted
    
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
    
    def update_server_info(
        self, 
        server_id: str, 
        server_name: str = None,
        server_version: str = None,
        protocol_version: str = None,
        server_capabilities: Dict[str, Any] = None,
        implementation_info: Dict[str, Any] = None,
        response_time_ms: int = None
    ) -> bool:
        """Update server introspected information and performance metrics."""
        with self._get_cursor() as cursor:
            # Build dynamic update query
            updates = []
            params = []
            
            if server_name is not None:
                updates.append("server_name = ?")
                params.append(server_name)
            
            if server_version is not None:
                updates.append("server_version = ?")
                params.append(server_version)
            
            if protocol_version is not None:
                updates.append("protocol_version = ?")
                params.append(protocol_version)
            
            if server_capabilities is not None:
                updates.append("server_capabilities = ?")
                params.append(json.dumps(server_capabilities))
            
            if implementation_info is not None:
                updates.append("implementation_info = ?")
                params.append(json.dumps(implementation_info))
            
            # Update performance metrics
            if response_time_ms is not None:
                updates.append("last_ping_time = ?")
                params.append(datetime.utcnow())
                
                # Update average response time (simple moving average)
                cursor.execute("SELECT avg_response_time_ms, total_discoveries FROM servers WHERE id = ?", (server_id,))
                row = cursor.fetchone()
                if row:
                    current_avg = row['avg_response_time_ms'] or 0
                    total_discoveries = row['total_discoveries'] or 0
                    
                    if total_discoveries > 0:
                        new_avg = ((current_avg * total_discoveries) + response_time_ms) // (total_discoveries + 1)
                    else:
                        new_avg = response_time_ms
                    
                    updates.append("avg_response_time_ms = ?")
                    params.append(new_avg)
            
            # Always update the updated_at timestamp
            updates.append("updated_at = ?")
            params.append(datetime.utcnow())
            
            # Add server_id for WHERE clause
            params.append(server_id)
            
            if updates:
                query = f"UPDATE servers SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                return cursor.rowcount > 0
            
            return False
    
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
    
    def store_capabilities(self, server_id: str, capabilities: List[ServerCapability]) -> int:
        """Store discovered capabilities for a server."""
        with self._get_cursor() as cursor:
            # Clear existing capabilities for this server
            cursor.execute("DELETE FROM server_capabilities WHERE server_id = ?", (server_id,))
            
            # Insert new capabilities
            stored_count = 0
            for capability in capabilities:
                try:
                    cursor.execute("""
                        INSERT INTO server_capabilities (
                            server_id, type, name, description, input_schema, 
                            output_schema, uri_template, discovered_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        server_id,
                        capability.type,
                        capability.name,
                        capability.description,
                        json.dumps(capability.input_schema) if capability.input_schema else "{}",
                        json.dumps(capability.output_schema) if capability.output_schema else "{}",
                        capability.uri_template,
                        capability.discovered_at
                    ))
                    
                    # Get the auto-generated ID and update the capability object
                    capability_id = cursor.lastrowid
                    capability.id = capability_id
                    
                    stored_count += 1
                except Exception as e:
                    # Log error but continue with other capabilities
                    print(f"Warning: Failed to store capability {capability.name}: {e}")
            
            return stored_count
    
    def get_server_capabilities(self, server_id: str, capability_type: str = None) -> List[CapabilityModel]:
        """Get capabilities for a server, optionally filtered by type."""
        query = "SELECT * FROM server_capabilities WHERE server_id = ?"
        params = [server_id]
        
        if capability_type:
            query += " AND type = ?"
            params.append(capability_type)
        
        query += " ORDER BY type, name"
        
        capabilities = []
        with self._get_cursor() as cursor:
            cursor.execute(query, params)
            for row in cursor.fetchall():
                # Handle datetime parsing more robustly
                discovered_at = None
                if row['discovered_at']:
                    try:
                        if isinstance(row['discovered_at'], str):
                            # Handle ISO format strings
                            discovered_at = datetime.fromisoformat(row['discovered_at'].replace('Z', '+00:00'))
                        else:
                            # Handle datetime objects from SQLite
                            discovered_at = row['discovered_at']
                    except (ValueError, TypeError):
                        # Fallback to current time if parsing fails
                        discovered_at = datetime.utcnow()
                
                capabilities.append(CapabilityModel(
                    id=row['id'],
                    server_id=row['server_id'],
                    type=row['type'],
                    name=row['name'],
                    description=row['description'],
                    input_schema=row['input_schema'],
                    output_schema=row['output_schema'],
                    uri_template=row['uri_template'],
                    discovered_at=discovered_at,
                ))
        
        return capabilities
    
    def search_capabilities(
        self, 
        query: str = None, 
        capability_type: str = None,
        server_id: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[CapabilityModel], int]:
        """Search capabilities with optional filters."""
        base_query = "SELECT * FROM server_capabilities"
        count_query = "SELECT COUNT(*) FROM server_capabilities"
        conditions = []
        params = []
        
        if query:
            conditions.append("(name LIKE ? OR description LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])
        
        if capability_type:
            conditions.append("type = ?")
            params.append(capability_type)
        
        if server_id:
            conditions.append("server_id = ?")
            params.append(server_id)
        
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)
            base_query += where_clause
            count_query += where_clause
        
        base_query += " ORDER BY type, name LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        capabilities = []
        total = 0
        
        with self._get_cursor() as cursor:
            # Get total count
            cursor.execute(count_query, params[:-2])  # Exclude limit/offset for count
            total = cursor.fetchone()[0]
            
            # Get results
            cursor.execute(base_query, params)
            for row in cursor.fetchall():
                # Handle datetime parsing more robustly
                discovered_at = None
                if row['discovered_at']:
                    try:
                        if isinstance(row['discovered_at'], str):
                            # Handle ISO format strings
                            discovered_at = datetime.fromisoformat(row['discovered_at'].replace('Z', '+00:00'))
                        else:
                            # Handle datetime objects from SQLite
                            discovered_at = row['discovered_at']
                    except (ValueError, TypeError):
                        # Fallback to current time if parsing fails
                        discovered_at = datetime.utcnow()
                
                capabilities.append(CapabilityModel(
                    id=row['id'],
                    server_id=row['server_id'],
                    type=row['type'],
                    name=row['name'],
                    description=row['description'],
                    input_schema=row['input_schema'],
                    output_schema=row['output_schema'],
                    uri_template=row['uri_template'],
                    discovered_at=discovered_at,
                ))
        
        return capabilities, total
    
    def record_discovery_attempt(
        self, 
        server_id: str, 
        status: str, 
        capabilities_found: int = 0,
        error_message: str = None,
        discovery_time_ms: int = None
    ) -> int:
        """Record a capability discovery attempt."""
        with self._get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO capability_discoveries (
                    server_id, status, capabilities_found, error_message, 
                    discovery_time_ms, discovered_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                server_id, status, capabilities_found, error_message,
                discovery_time_ms, datetime.utcnow()
            ))
            return cursor.lastrowid
    
    def get_discovery_history(self, server_id: str, limit: int = 10) -> List[DiscoveryModel]:
        """Get capability discovery history for a server."""
        discoveries = []
        with self._get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM capability_discoveries 
                WHERE server_id = ? 
                ORDER BY discovered_at DESC 
                LIMIT ?
            """, (server_id, limit))
            
            for row in cursor.fetchall():
                discoveries.append(DiscoveryModel(
                    id=row['id'],
                    server_id=row['server_id'],
                    status=row['status'],
                    capabilities_found=row['capabilities_found'],
                    error_message=row['error_message'],
                    discovery_time_ms=row['discovery_time_ms'],
                    discovered_at=datetime.fromisoformat(row['discovered_at'].replace('Z', '+00:00')) if row['discovered_at'] else None,
                ))
        
        return discoveries
    
    def get_capability_stats(self) -> Dict[str, Any]:
        """Get capability statistics across all servers."""
        with self._get_cursor() as cursor:
            # Total capabilities by type
            cursor.execute("""
                SELECT type, COUNT(*) as count 
                FROM server_capabilities 
                GROUP BY type
            """)
            capability_counts = {row['type']: row['count'] for row in cursor.fetchall()}
            
            # Servers with capabilities
            cursor.execute("""
                SELECT COUNT(DISTINCT server_id) as count 
                FROM server_capabilities
            """)
            servers_with_capabilities = cursor.fetchone()['count']
            
            # Recent discoveries
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM capability_discoveries 
                WHERE discovered_at > datetime('now', '-24 hours')
                GROUP BY status
            """)
            recent_discoveries = {row['status']: row['count'] for row in cursor.fetchall()}
            
            return {
                "capability_counts": capability_counts,
                "servers_with_capabilities": servers_with_capabilities,
                "recent_discoveries": recent_discoveries,
                "total_capabilities": sum(capability_counts.values()),
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