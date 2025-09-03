#!/usr/bin/env python3
"""
Quick test to verify the proxy server fix works correctly.
"""

import asyncio
from fastmcp import FastMCP
from fastmcp.client import Client
from mcp_proxy_server import create_proxy_server


async def test_proxy_fix():
    """Test that the proxy server can be created without errors."""
    print("Testing proxy server fix...")
    
    # Create a simple test server
    test_server = FastMCP("TestServer")
    
    @test_server.tool
    def hello(name: str) -> str:
        """Say hello to someone."""
        return f"Hello, {name}!"
    
    print("✅ Created test server")
    
    # Test the proxy creation (this should not fail now)
    try:
        proxy_server = FastMCP.as_proxy(test_server, name="TestProxy")
        print("✅ Created proxy server successfully")
        
        # Test that we can use the proxy
        async with Client(proxy_server) as client:
            tools = await client.list_tools()
            print(f"✅ Found {len(tools)} tools via proxy: {[t.name for t in tools]}")
            
            result = await client.call_tool("hello", {"name": "World"})
            print(f"✅ Tool call result: {result[0].text}")
            
        print("🎉 All tests passed! The fix works correctly.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_proxy_fix())