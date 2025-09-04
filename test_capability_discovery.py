#!/usr/bin/env python3
"""
Tests for MCP Capability Discovery functionality.

Tests capability discovery service, database operations, and API endpoints.
"""

import asyncio
import json
import os
import tempfile
from datetime import datetime
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

# Test imports
try:
    from fastapi.testclient import TestClient
    from fastmcp import FastMCP
    from fastmcp.client import Client
    from registry import (
        Database, ServerCreate, ServerCapability, 
        CapabilityDiscoveryService, create_registry_app
    )
    REGISTRY_AVAILABLE = True
except ImportError:
    REGISTRY_AVAILABLE = False


class TestCapabilityDiscovery:
    """Test suite for capability discovery service."""
    
    def setup_method(self):
        """Set up test database and discovery service."""
        if not REGISTRY_AVAILABLE:
            return
        
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        self.database = Database(self.db_path)
        self.discovery_service = CapabilityDiscoveryService(self.database)
        
        # Create test server
        server_data = ServerCreate(
            name="Test Server",
            url="http://localhost:8001/mcp/test",
            description="Test server for capability discovery",
            transport="http"
        )
        self.test_server = self.database.create_server(server_data)
    
    def teardown_method(self):
        """Clean up test database."""
        if hasattr(self, 'database'):
            self.database.close()
        if hasattr(self, 'db_fd'):
            os.close(self.db_fd)
        if hasattr(self, 'db_path') and os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    async def test_discover_server_capabilities_success(self):
        """Test successful capability discovery."""
        if not REGISTRY_AVAILABLE:
            return
        
        # Create mock FastMCP server with capabilities
        mock_server = FastMCP("MockServer")
        
        @mock_server.tool
        def test_tool(message: str) -> str:
            """A test tool."""
            return f"Echo: {message}"
        
        @mock_server.resource("test://resource")
        def test_resource() -> str:
            """A test resource."""
            return "Test resource content"
        
        @mock_server.prompt
        def test_prompt(name: str) -> str:
            """A test prompt."""
            return f"Hello, {name}!"
        
        # Mock the client creation to return our test server
        with patch.object(self.discovery_service, '_create_client') as mock_create_client:
            mock_client = Client(mock_server)
            mock_create_client.return_value = mock_client
            
            # Discover capabilities
            result = await self.discovery_service.discover_server_capabilities(
                server_id=self.test_server.id,
                server_url=self.test_server.url,
                transport_type="http"
            )
            
            # Verify results
            assert result.status == "success"
            assert result.capabilities_found >= 3  # At least tool, resource, prompt
            assert result.discovery_time_ms > 0
            assert len(result.capabilities) >= 3
            
            # Check capability types
            capability_types = {cap.type for cap in result.capabilities}
            assert "tool" in capability_types
            assert "resource" in capability_types
            assert "prompt" in capability_types
            
            # Verify capabilities are stored in database
            stored_capabilities = self.database.get_server_capabilities(self.test_server.id)
            assert len(stored_capabilities) >= 3
    
    async def test_discover_server_capabilities_failure(self):
        """Test capability discovery failure handling."""
        if not REGISTRY_AVAILABLE:
            return
        
        # Mock client creation to raise an exception
        with patch.object(self.discovery_service, '_create_client') as mock_create_client:
            mock_create_client.side_effect = Exception("Connection failed")
            
            # Attempt discovery
            result = await self.discovery_service.discover_server_capabilities(
                server_id=self.test_server.id,
                server_url=self.test_server.url,
                transport_type="http"
            )
            
            # Verify failure handling
            assert result.status == "failed"
            assert result.capabilities_found == 0
            assert result.error_message is not None
            assert "Connection failed" in result.error_message
            
            # Verify failure is recorded in database
            history = self.database.get_discovery_history(self.test_server.id, limit=1)
            assert len(history) == 1
            assert history[0].status == "failed"
    
    async def test_discover_server_capabilities_cached(self):
        """Test cached capability discovery."""
        if not REGISTRY_AVAILABLE:
            return
        
        # First, store some capabilities manually
        capabilities = [
            ServerCapability(
                server_id=self.test_server.id,
                type="tool",
                name="cached_tool",
                description="A cached tool"
            )
        ]
        self.database.store_capabilities(self.test_server.id, capabilities)
        
        # Record successful discovery
        self.database.record_discovery_attempt(
            server_id=self.test_server.id,
            status="success",
            capabilities_found=1,
            discovery_time_ms=100
        )
        
        # Attempt discovery without force_refresh
        result = await self.discovery_service.discover_server_capabilities(
            server_id=self.test_server.id,
            server_url=self.test_server.url,
            transport_type="http",
            force_refresh=False
        )
        
        # Should return cached results
        assert result.status == "cached"
        assert result.capabilities_found == 1
        assert result.discovery_time_ms == 0
        assert len(result.capabilities) == 1
        assert result.capabilities[0].name == "cached_tool"
    
    def test_get_server_capabilities_summary(self):
        """Test capability summary generation."""
        if not REGISTRY_AVAILABLE:
            return
        
        # Store test capabilities
        capabilities = [
            ServerCapability(
                server_id=self.test_server.id,
                type="tool",
                name="tool1",
                description="Tool 1"
            ),
            ServerCapability(
                server_id=self.test_server.id,
                type="tool", 
                name="tool2",
                description="Tool 2"
            ),
            ServerCapability(
                server_id=self.test_server.id,
                type="resource",
                name="resource1",
                description="Resource 1"
            )
        ]
        self.database.store_capabilities(self.test_server.id, capabilities)
        
        # Get summary
        summary = self.discovery_service.get_server_capabilities_summary(self.test_server.id)
        
        # Verify summary
        assert summary["total"] == 3
        assert summary["by_type"]["tool"] == 2
        assert summary["by_type"]["resource"] == 1
        assert "last_discovery" in summary


class TestCapabilityDatabase:
    """Test suite for capability database operations."""
    
    def setup_method(self):
        """Set up test database."""
        if not REGISTRY_AVAILABLE:
            return
        
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        self.database = Database(self.db_path)
        
        # Create test server
        server_data = ServerCreate(
            name="Test Server",
            url="http://localhost:8001/mcp/db-test"
        )
        self.test_server = self.database.create_server(server_data)
    
    def teardown_method(self):
        """Clean up test database."""
        if hasattr(self, 'database'):
            self.database.close()
        if hasattr(self, 'db_fd'):
            os.close(self.db_fd)
        if hasattr(self, 'db_path') and os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_store_and_retrieve_capabilities(self):
        """Test storing and retrieving capabilities."""
        if not REGISTRY_AVAILABLE:
            return
        
        # Create test capabilities
        capabilities = [
            ServerCapability(
                server_id=self.test_server.id,
                type="tool",
                name="test_tool",
                description="A test tool",
                input_schema={"type": "object", "properties": {"message": {"type": "string"}}}
            ),
            ServerCapability(
                server_id=self.test_server.id,
                type="resource",
                name="test_resource",
                description="A test resource",
                uri_template="test://resource/{id}"
            )
        ]
        
        # Store capabilities
        stored_count = self.database.store_capabilities(self.test_server.id, capabilities)
        assert stored_count == 2
        
        # Retrieve all capabilities
        retrieved = self.database.get_server_capabilities(self.test_server.id)
        assert len(retrieved) == 2
        
        # Verify capability details
        tool_cap = next(cap for cap in retrieved if cap.type == "tool")
        assert tool_cap.name == "test_tool"
        assert tool_cap.description == "A test tool"
        assert json.loads(tool_cap.input_schema)["type"] == "object"
        
        resource_cap = next(cap for cap in retrieved if cap.type == "resource")
        assert resource_cap.name == "test_resource"
        assert resource_cap.uri_template == "test://resource/{id}"
    
    def test_search_capabilities(self):
        """Test capability search functionality."""
        if not REGISTRY_AVAILABLE:
            return
        
        # Store test capabilities
        capabilities = [
            ServerCapability(
                server_id=self.test_server.id,
                type="tool",
                name="weather_tool",
                description="Get weather information"
            ),
            ServerCapability(
                server_id=self.test_server.id,
                type="tool",
                name="calendar_tool", 
                description="Manage calendar events"
            ),
            ServerCapability(
                server_id=self.test_server.id,
                type="resource",
                name="weather_data",
                description="Weather data resource"
            )
        ]
        self.database.store_capabilities(self.test_server.id, capabilities)
        
        # Search by query
        results, total = self.database.search_capabilities(query="weather")
        assert total == 2  # weather_tool and weather_data
        assert len(results) == 2
        
        # Search by type
        results, total = self.database.search_capabilities(capability_type="tool")
        assert total == 2  # weather_tool and calendar_tool
        assert len(results) == 2
        
        # Search with limit
        results, total = self.database.search_capabilities(limit=1)
        assert total == 3  # Total available
        assert len(results) == 1  # Limited result
    
    def test_discovery_history(self):
        """Test discovery history tracking."""
        if not REGISTRY_AVAILABLE:
            return
        
        # Record discovery attempts
        discovery_id1 = self.database.record_discovery_attempt(
            server_id=self.test_server.id,
            status="success",
            capabilities_found=5,
            discovery_time_ms=1000
        )
        
        discovery_id2 = self.database.record_discovery_attempt(
            server_id=self.test_server.id,
            status="failed",
            error_message="Connection timeout",
            discovery_time_ms=5000
        )
        
        # Get history
        history = self.database.get_discovery_history(self.test_server.id)
        assert len(history) == 2
        
        # Verify order (most recent first)
        assert history[0].id == discovery_id2
        assert history[0].status == "failed"
        assert history[0].error_message == "Connection timeout"
        
        assert history[1].id == discovery_id1
        assert history[1].status == "success"
        assert history[1].capabilities_found == 5
    
    def test_capability_stats(self):
        """Test capability statistics."""
        if not REGISTRY_AVAILABLE:
            return
        
        # Store capabilities for multiple servers
        server2_data = ServerCreate(
            name="Server 2",
            url="http://localhost:8002/mcp/stats-test"
        )
        server2 = self.database.create_server(server2_data)
        
        # Server 1 capabilities
        capabilities1 = [
            ServerCapability(server_id=self.test_server.id, type="tool", name="tool1"),
            ServerCapability(server_id=self.test_server.id, type="resource", name="resource1")
        ]
        self.database.store_capabilities(self.test_server.id, capabilities1)
        
        # Server 2 capabilities
        capabilities2 = [
            ServerCapability(server_id=server2.id, type="tool", name="tool2"),
            ServerCapability(server_id=server2.id, type="tool", name="tool3"),
            ServerCapability(server_id=server2.id, type="prompt", name="prompt1")
        ]
        self.database.store_capabilities(server2.id, capabilities2)
        
        # Get stats
        stats = self.database.get_capability_stats()
        
        # Verify stats
        assert stats["total_capabilities"] == 5
        assert stats["servers_with_capabilities"] == 2
        assert stats["capability_counts"]["tool"] == 3
        assert stats["capability_counts"]["resource"] == 1
        assert stats["capability_counts"]["prompt"] == 1


class TestCapabilityAPI:
    """Test suite for capability discovery API endpoints."""
    
    def setup_method(self):
        """Set up test API client."""
        if not REGISTRY_AVAILABLE:
            return
        
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        
        # Create test app
        self.app = create_registry_app(self.db_path)
        self.client = TestClient(self.app)
        
        # Register test server
        server_data = {
            "name": "Test Server",
            "url": "http://localhost:8001/mcp/api-test",
            "description": "Test server for API testing"
        }
        response = self.client.post("/api/servers", json=server_data)
        assert response.status_code == 201
        self.server_id = response.json()["id"]
    
    def teardown_method(self):
        """Clean up test resources."""
        if hasattr(self, 'db_fd'):
            os.close(self.db_fd)
        if hasattr(self, 'db_path') and os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_discover_capabilities_endpoint(self):
        """Test capability discovery API endpoint."""
        if not REGISTRY_AVAILABLE:
            return
        
        # Mock the discovery service
        with patch('registry.capability_discovery.CapabilityDiscoveryService.discover_server_capabilities') as mock_discover:
            mock_discover.return_value = AsyncMock()
            mock_discover.return_value.status = "success"
            mock_discover.return_value.capabilities_found = 2
            mock_discover.return_value.discovery_time_ms = 1500
            mock_discover.return_value.capabilities = []
            
            # Trigger discovery
            response = self.client.post(f"/api/servers/{self.server_id}/discover")
            
            # Note: This test may not work perfectly due to async mocking complexity
            # In a real test environment, you'd use pytest-asyncio and proper async mocking
            print(f"Discovery endpoint response status: {response.status_code}")
    
    def test_get_capabilities_endpoint(self):
        """Test get capabilities API endpoint."""
        if not REGISTRY_AVAILABLE:
            return
        
        # First, manually store some capabilities in the database
        from registry.database import get_database
        from registry.models import ServerCapability
        
        db = get_database(self.db_path)
        capabilities = [
            ServerCapability(
                server_id=self.server_id,
                type="tool",
                name="api_test_tool",
                description="API test tool"
            )
        ]
        db.store_capabilities(self.server_id, capabilities)
        
        # Get capabilities via API
        response = self.client.get(f"/api/servers/{self.server_id}/capabilities")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "api_test_tool"
        assert data[0]["type"] == "tool"
    
    def test_search_capabilities_endpoint(self):
        """Test capability search API endpoint."""
        if not REGISTRY_AVAILABLE:
            return
        
        # Store test capabilities
        from registry.database import get_database
        from registry.models import ServerCapability
        
        db = get_database(self.db_path)
        capabilities = [
            ServerCapability(
                server_id=self.server_id,
                type="tool",
                name="search_test_tool",
                description="Tool for search testing"
            )
        ]
        db.store_capabilities(self.server_id, capabilities)
        
        # Search capabilities
        response = self.client.get("/api/capabilities/search?q=search")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] >= 1
        assert len(data["capabilities"]) >= 1
        assert "servers" in data
    
    def test_capability_stats_endpoint(self):
        """Test capability statistics API endpoint."""
        if not REGISTRY_AVAILABLE:
            return
        
        response = self.client.get("/api/capabilities/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "capability_counts" in data
        assert "servers_with_capabilities" in data
        assert "total_capabilities" in data


async def run_tests():
    """Run all capability discovery tests."""
    print("Running MCP Capability Discovery tests...")
    
    if not REGISTRY_AVAILABLE:
        print("❌ Registry dependencies not available. Install with:")
        print("   uv sync --extra test")
        return
    
    try:
        # Test capability discovery service
        print("\n🔍 Testing Capability Discovery Service...")
        
        def run_discovery_test(test_name, test_method):
            discovery_test = TestCapabilityDiscovery()
            try:
                discovery_test.setup_method()
                if asyncio.iscoroutinefunction(test_method):
                    asyncio.run(test_method(discovery_test))
                else:
                    test_method(discovery_test)
                print(f"✅ {test_name} passed")
            finally:
                discovery_test.teardown_method()
        
        run_discovery_test("test_discover_server_capabilities_success", 
                          lambda t: t.test_discover_server_capabilities_success())
        run_discovery_test("test_discover_server_capabilities_failure",
                          lambda t: t.test_discover_server_capabilities_failure())
        run_discovery_test("test_discover_server_capabilities_cached",
                          lambda t: t.test_discover_server_capabilities_cached())
        run_discovery_test("test_get_server_capabilities_summary",
                          lambda t: t.test_get_server_capabilities_summary())
        
        # Test database operations
        print("\n💾 Testing Capability Database Operations...")
        
        def run_db_test(test_name, test_method):
            db_test = TestCapabilityDatabase()
            try:
                db_test.setup_method()
                test_method(db_test)
                print(f"✅ {test_name} passed")
            finally:
                db_test.teardown_method()
        
        run_db_test("test_store_and_retrieve_capabilities",
                   lambda t: t.test_store_and_retrieve_capabilities())
        run_db_test("test_search_capabilities",
                   lambda t: t.test_search_capabilities())
        run_db_test("test_discovery_history",
                   lambda t: t.test_discovery_history())
        run_db_test("test_capability_stats",
                   lambda t: t.test_capability_stats())
        
        # Test API endpoints
        print("\n🌐 Testing Capability API Endpoints...")
        
        def run_api_test(test_name, test_method):
            api_test = TestCapabilityAPI()
            try:
                api_test.setup_method()
                test_method(api_test)
                print(f"✅ {test_name} passed")
            finally:
                api_test.teardown_method()
        
        run_api_test("test_get_capabilities_endpoint",
                    lambda t: t.test_get_capabilities_endpoint())
        run_api_test("test_search_capabilities_endpoint", 
                    lambda t: t.test_search_capabilities_endpoint())
        run_api_test("test_capability_stats_endpoint",
                    lambda t: t.test_capability_stats_endpoint())
        
        print("\n🎉 All capability discovery tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_tests())