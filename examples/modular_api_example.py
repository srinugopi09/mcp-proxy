#!/usr/bin/env python3
"""
Example demonstrating the new modular MCP Registry API.

This example shows how to:
1. Initialize the database
2. Create the FastAPI app
3. Register servers programmatically
4. Query capabilities
"""

import asyncio
from mcp_registry.core.database import init_database_sync, get_session_maker
from mcp_registry.api.app import create_app
from mcp_registry.models.server import ServerCreate
from mcp_registry.services.registry import RegistryService


async def main():
    """Demonstrate the modular API usage."""
    print("🚀 MCP Registry Modular API Example")
    print("=" * 50)
    
    # 1. Initialize database
    print("\n1. Initializing database...")
    init_database_sync()
    print("✅ Database initialized")
    
    # 2. Create FastAPI app
    print("\n2. Creating FastAPI application...")
    app = create_app()
    print("✅ FastAPI app created")
    
    # 3. Register a server programmatically
    print("\n3. Registering a sample server...")
    session_maker = get_session_maker()
    async with session_maker() as session:
        registry_service = RegistryService(session)
        
        server_data = ServerCreate(
            name="Example MCP Server",
            url="http://localhost:3000/mcp",
            description="A sample MCP server for demonstration",
            tags=["example", "demo"],
            transport="http"
        )
        
        try:
            server = await registry_service.create_server(server_data)
            print(f"✅ Server registered: {server['name']}")
            print(f"   ID: {server['id']}")
            print(f"   Endpoint: {server['endpoint']}")
        except Exception as e:
            print(f"⚠️  Server might already exist: {e}")
    
    # 4. List all servers
    print("\n4. Listing all registered servers...")
    session_maker = get_session_maker()
    async with session_maker() as session:
        registry_service = RegistryService(session)
        servers = await registry_service.list_servers()
        
        if servers:
            for server in servers:
                print(f"   📋 {server['name']} ({server['id']})")
                print(f"      URL: {server['url']}")
                print(f"      Status: {server['status']}")
        else:
            print("   No servers registered")
    
    print("\n🎉 Example completed!")
    print("\nTo start the API server, run:")
    print("   mcp-registry start --debug")
    print("\nThen visit: http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(main())