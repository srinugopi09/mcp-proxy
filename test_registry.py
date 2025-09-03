#!/usr/bin/env python3
"""
Tests for MCP Server Registry functionality.

Tests database operations, API endpoints, and integration with the proxy server.
"""

import asyncio
import json
import os
import tempfile
import pytest
from datetime import datetime
from typing import Dict, Any
from unittest.mock import patch, MagicMock

# Test imports
try:
    from fastapi.testclient import TestClient
    from registry import Database, ServerCreate, ServerUpdate, create_registry_app
    REGISTRY_AVAILABLE = True
except ImportError:
    REGISTRY_AVAILABLE = False


class TestDatabase:
    """Test suite for database operations."""
    
    def setup_method(self):
        """Set up test database."""
        if not REGISTRY_AVAILABLE:
            pytest.skip("Registry dependencies not available")
        
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        self.database = Database(self.db_path)
    
    def teardown_method(self):
        """Clean up test database."""
        if hasattr(self, 'database'):
            self.database.close()
        if hasattr(self, 'db_fd'):
            os.close(self.db_fd)
        if hasattr(self, 'db_path') and os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_create_server(self):
        """Test server creation."""
        server_data = ServerCreate(
            name="Test Server",
            url="http://localhost:8001/mcp",
            description="A test server",
            tags=["test", "example"],
            transport="http"
        )
        
        server = self.database.create_server(server_data)
        
        assert server.id is not None
        assert server.name == "Test Server"
        assert server.url == "http://localhost:8001/mcp"
        assert server.description == "A test server"
        assert json.loads(server.tags) == ["test", "example"]
        assert server.transport == "http"
        assert server.status == "unknown"
        assert server.created_at is not None
        assert server.updated_at is not None
    
    def test_get_server(self):
        """Test server retrieval by ID."""
        # Create a server
        server_data = ServerCreate(
            name="Test Server",
            url="http://localhost:8001/mcp"
        )
        created_server = self.database.create_server(server_data)
        
        # Retrieve the server
        retrieved_server = self.database.get_server(created_server.id)
        
        assert retrieved_server is not None
        assert retrieved_server.id == created_server.id
        assert retrieved_server.name == "Test Server"
        assert retrieved_server.url == "http://localhost:8001/mcp"
    
    def test_get_server_by_url(self):
        """Test server retrieval by URL."""
        server_data = ServerCreate(
            name="Test Server",
            url="http://localhost:8001/mcp"
        )
        created_server = self.database.create_server(server_data)
        
        retrieved_server = self.database.get_server_by_url("http://localhost:8001/mcp")
        
        assert retrieved_server is not None
        assert retrieved_server.id == created_server.id
        assert retrieved_server.url == "http://localhost:8001/mcp"
    
    def test_list_servers(self):
        """Test server listing."""
        # Create multiple servers
        servers_data = [
            ServerCreate(name="Server 1", url="http://localhost:8001/mcp", tags=["test"]),
            ServerCreate(name="Server 2", url="http://localhost:8002/mcp", tags=["prod"]),
            ServerCreate(name="Server 3", url="http://localhost:8003/mcp", tags=["test", "api"]),
        ]
        
        created_servers = []
        for server_data in servers_data:
            created_servers.append(self.database.create_server(server_data))
        
        # Test listing all servers
        all_servers = self.database.list_servers()
        assert len(all_servers) == 3
        
        # Test filtering by tags
        test_servers = self.database.list_servers(tags=["test"])
        assert len(test_servers) == 2
        
        # Test limit and offset
        limited_servers = self.database.list_servers(limit=2)
        assert len(limited_servers) == 2
        
        offset_servers = self.database.list_servers(limit=2, offset=1)
        assert len(offset_servers) == 2
    
    def test_update_server(self):
        """Test server updates."""
        # Create a server
        server_data = ServerCreate(
            name="Original Server",
            url="http://localhost:8001/mcp"
        )
        created_server = self.database.create_server(server_data)
        
        # Update the server
        update_data = ServerUpdate(
            name="Updated Server",
            description="Updated description",
            tags=["updated"]
        )
        updated_server = self.database.update_server(created_server.id, update_data)
        
        assert updated_server is not None
        assert updated_server.name == "Updated Server"
        assert updated_server.description == "Updated description"
        assert json.loads(updated_server.tags) == ["updated"]
        assert updated_server.url == "http://localhost:8001/mcp"  # Unchanged
    
    def test_delete_server(self):
        """Test server deletion."""
        server_data = ServerCreate(
            name="Test Server",
            url="http://localhost:8001/mcp"
        )
        created_server = self.database.create_server(server_data)
        
        # Delete the server
        success = self.database.delete_server(created_server.id)
        assert success is True
        
        # Verify deletion
        retrieved_server = self.database.get_server(created_server.id)
        assert retrieved_server is None
    
    def test_update_server_status(self):
        """Test server status updates."""
        server_data = ServerCreate(
            name="Test Server",
            url="http://localhost:8001/mcp"
        )
        created_server = self.database.create_server(server_data)
        
        # Update status
        success = self.database.update_server_status(created_server.id, "healthy")
        assert success is True
        
        # Verify status update
        updated_server = self.database.get_server(created_server.id)
        assert updated_server.status == "healthy"
        assert updated_server.last_checked is not None
    
    def test_get_stats(self):
        """Test registry statistics."""
        # Create servers with different statuses
        servers_data = [
            ServerCreate(name="Server 1", url="http://localhost:8001/mcp"),
            ServerCreate(name="Server 2", url="http://localhost:8002/mcp", transport="sse"),
        ]
        
        for server_data in servers_data:
            server = self.database.create_server(server_data)
            self.database.update_server_status(server.id, "healthy")
        
        stats = self.database.get_stats()
        
        assert stats["total_servers"] == 2
        assert "healthy" in stats["status_breakdown"]
        assert stats["status_breakdown"]["healthy"] == 2
        assert "auto" in stats["transport_breakdown"]
        assert "sse" in stats["transport_breakdown"]


class TestRegistryAPI:
    """Test suite for FastAPI endpoints."""
    
    def setup_method(self):
        """Set up test API client."""
        if not REGISTRY_AVAILABLE:
            pytest.skip("Registry dependencies not available")
        
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        
        # Create test app
        self.app = create_registry_app(self.db_path)
        self.client = TestClient(self.app)
    
    def teardown_method(self):
        """Clean up test resources."""
        if hasattr(self, 'db_fd'):
            os.close(self.db_fd)
        if hasattr(self, 'db_path') and os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_register_server(self):
        """Test server registration endpoint."""
        server_data = {
            "name": "Test Server",
            "url": "http://localhost:8001/mcp",
            "description": "A test server",
            "tags": ["test", "example"],
            "transport": "http"
        }
        
        response = self.client.post("/api/servers", json=server_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["name"] == "Test Server"
        assert data["url"] == "http://localhost:8001/mcp"
        assert data["description"] == "A test server"
        assert data["tags"] == ["test", "example"]
        assert data["transport"] == "http"
        assert data["status"] == "unknown"
        assert "id" in data
        assert "created_at" in data
    
    def test_register_duplicate_url(self):
        """Test registration with duplicate URL."""
        server_data = {
            "name": "Test Server",
            "url": "http://localhost:8001/mcp"
        }
        
        # Register first server
        response1 = self.client.post("/api/servers", json=server_data)
        assert response1.status_code == 201
        
        # Try to register duplicate URL
        response2 = self.client.post("/api/servers", json=server_data)
        assert response2.status_code == 409
        assert "already registered" in response2.json()["detail"]
    
    def test_list_servers(self):
        """Test server listing endpoint."""
        # Register multiple servers
        servers = [
            {"name": "Server 1", "url": "http://localhost:8001/mcp", "tags": ["test"]},
            {"name": "Server 2", "url": "http://localhost:8002/mcp", "tags": ["prod"]},
        ]
        
        for server_data in servers:
            response = self.client.post("/api/servers", json=server_data)
            assert response.status_code == 201
        
        # List all servers
        response = self.client.get("/api/servers")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] in ["Server 1", "Server 2"]
    
    def test_get_server(self):
        """Test get server endpoint."""
        # Register a server
        server_data = {
            "name": "Test Server",
            "url": "http://localhost:8001/mcp"
        }
        
        response = self.client.post("/api/servers", json=server_data)
        assert response.status_code == 201
        server_id = response.json()["id"]
        
        # Get the server
        response = self.client.get(f"/api/servers/{server_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == server_id
        assert data["name"] == "Test Server"
    
    def test_get_nonexistent_server(self):
        """Test getting a non-existent server."""
        response = self.client.get("/api/servers/nonexistent-id")
        assert response.status_code == 404
    
    def test_update_server(self):
        """Test server update endpoint."""
        # Register a server
        server_data = {
            "name": "Original Server",
            "url": "http://localhost:8001/mcp"
        }
        
        response = self.client.post("/api/servers", json=server_data)
        assert response.status_code == 201
        server_id = response.json()["id"]
        
        # Update the server
        update_data = {
            "name": "Updated Server",
            "description": "Updated description"
        }
        
        response = self.client.put(f"/api/servers/{server_id}", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "Updated Server"
        assert data["description"] == "Updated description"
        assert data["url"] == "http://localhost:8001/mcp"  # Unchanged
    
    def test_delete_server(self):
        """Test server deletion endpoint."""
        # Register a server
        server_data = {
            "name": "Test Server",
            "url": "http://localhost:8001/mcp"
        }
        
        response = self.client.post("/api/servers", json=server_data)
        assert response.status_code == 201
        server_id = response.json()["id"]
        
        # Delete the server
        response = self.client.delete(f"/api/servers/{server_id}")
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
        
        # Verify deletion
        response = self.client.get(f"/api/servers/{server_id}")
        assert response.status_code == 404
    
    def test_update_server_status(self):
        """Test server status update endpoint."""
        # Register a server
        server_data = {
            "name": "Test Server",
            "url": "http://localhost:8001/mcp"
        }
        
        response = self.client.post("/api/servers", json=server_data)
        assert response.status_code == 201
        server_id = response.json()["id"]
        
        # Update status
        status_data = {"status": "healthy"}
        response = self.client.patch(f"/api/servers/{server_id}/status", json=status_data)
        assert response.status_code == 200
        
        # Verify status update
        response = self.client.get(f"/api/servers/{server_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_get_stats(self):
        """Test statistics endpoint."""
        # Register a server
        server_data = {
            "name": "Test Server",
            "url": "http://localhost:8001/mcp"
        }
        
        response = self.client.post("/api/servers", json=server_data)
        assert response.status_code == 201
        
        # Get stats
        response = self.client.get("/api/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_servers"] == 1
        assert "status_breakdown" in data
        assert "transport_breakdown" in data


async def run_tests():
    """Run all tests manually (for environments without pytest)."""
    print("Running MCP Registry tests...")
    
    if not REGISTRY_AVAILABLE:
        print("❌ Registry dependencies not available. Install with:")
        print("   pip install fastapi uvicorn")
        return
    
    try:
        # Test database operations
        print("\n🧪 Testing Database Operations...")
        db_test = TestDatabase()
        
        db_test.setup_method()
        db_test.test_create_server()
        print("✅ test_create_server passed")
        
        db_test.test_get_server()
        print("✅ test_get_server passed")
        
        db_test.test_list_servers()
        print("✅ test_list_servers passed")
        
        db_test.test_update_server()
        print("✅ test_update_server passed")
        
        db_test.test_delete_server()
        print("✅ test_delete_server passed")
        
        db_test.test_update_server_status()
        print("✅ test_update_server_status passed")
        
        db_test.test_get_stats()
        print("✅ test_get_stats passed")
        
        db_test.teardown_method()
        
        # Test API endpoints
        print("\n🌐 Testing API Endpoints...")
        api_test = TestRegistryAPI()
        
        api_test.setup_method()
        api_test.test_health_check()
        print("✅ test_health_check passed")
        
        api_test.test_register_server()
        print("✅ test_register_server passed")
        
        api_test.test_list_servers()
        print("✅ test_list_servers passed")
        
        api_test.test_get_server()
        print("✅ test_get_server passed")
        
        api_test.test_update_server()
        print("✅ test_update_server passed")
        
        api_test.test_delete_server()
        print("✅ test_delete_server passed")
        
        api_test.test_update_server_status()
        print("✅ test_update_server_status passed")
        
        api_test.test_get_stats()
        print("✅ test_get_stats passed")
        
        api_test.teardown_method()
        
        print("\n🎉 All registry tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_tests())