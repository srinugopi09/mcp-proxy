#!/usr/bin/env python3
"""
Quick test to verify the registry test fixes work correctly.
"""

import asyncio
import tempfile
import os

try:
    from registry import Database, ServerCreate
    REGISTRY_AVAILABLE = True
except ImportError:
    REGISTRY_AVAILABLE = False


async def test_database_isolation():
    """Test that database isolation works correctly."""
    if not REGISTRY_AVAILABLE:
        print("❌ Registry dependencies not available")
        return False
    
    print("Testing database isolation fix...")
    
    # Test 1: Create server in first database
    db_fd1, db_path1 = tempfile.mkstemp(suffix='.db')
    try:
        database1 = Database(db_path1)
        server_data1 = ServerCreate(
            name="Test Server 1",
            url="http://localhost:8001/mcp"
        )
        server1 = database1.create_server(server_data1)
        print(f"✅ Created server 1: {server1.id}")
        database1.close()
    finally:
        os.close(db_fd1)
        if os.path.exists(db_path1):
            os.unlink(db_path1)
    
    # Test 2: Create server with same URL in second database (should work)
    db_fd2, db_path2 = tempfile.mkstemp(suffix='.db')
    try:
        database2 = Database(db_path2)
        server_data2 = ServerCreate(
            name="Test Server 2",
            url="http://localhost:8001/mcp"  # Same URL, different DB
        )
        server2 = database2.create_server(server_data2)
        print(f"✅ Created server 2: {server2.id}")
        database2.close()
    finally:
        os.close(db_fd2)
        if os.path.exists(db_path2):
            os.unlink(db_path2)
    
    print("✅ Database isolation test passed!")
    return True


async def test_unique_urls():
    """Test that unique URLs prevent conflicts."""
    if not REGISTRY_AVAILABLE:
        print("❌ Registry dependencies not available")
        return False
    
    print("Testing unique URL handling...")
    
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    try:
        database = Database(db_path)
        
        # Create first server
        server_data1 = ServerCreate(
            name="Server 1",
            url="http://localhost:8001/mcp/unique1"
        )
        server1 = database.create_server(server_data1)
        print(f"✅ Created server 1: {server1.id}")
        
        # Create second server with different URL
        server_data2 = ServerCreate(
            name="Server 2", 
            url="http://localhost:8001/mcp/unique2"
        )
        server2 = database.create_server(server_data2)
        print(f"✅ Created server 2: {server2.id}")
        
        # Try to create server with duplicate URL (should fail)
        try:
            server_data3 = ServerCreate(
                name="Server 3",
                url="http://localhost:8001/mcp/unique1"  # Duplicate URL
            )
            server3 = database.create_server(server_data3)
            print("❌ Should have failed with duplicate URL")
            return False
        except Exception as e:
            print(f"✅ Correctly rejected duplicate URL: {type(e).__name__}")
        
        database.close()
    finally:
        os.close(db_fd)
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    print("✅ Unique URL test passed!")
    return True


async def main():
    """Run all fix verification tests."""
    print("🧪 Testing Registry Fixes...")
    
    success1 = await test_database_isolation()
    success2 = await test_unique_urls()
    
    if success1 and success2:
        print("\n🎉 All registry fixes working correctly!")
        return True
    else:
        print("\n❌ Some tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)