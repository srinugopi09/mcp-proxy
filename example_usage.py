#!/usr/bin/env python3
"""
Example usage of the MCP Proxy Server

This demonstrates how to use the proxy server both programmatically
and as a standalone script.
"""

import asyncio
from fastmcp import FastMCP
from fastmcp.client import Client
from mcp_proxy_server import create_proxy_server


async def example_programmatic_usage():
    """Example of using the proxy server programmatically."""
    print("=== Programmatic Usage Example ===")
    
    # First, create a sample "remote" server to proxy
    print("1. Creating a sample remote server...")
    remote_server = FastMCP("RemoteServer")
    
    @remote_server.tool
    def calculate(operation: str, a: float, b: float) -> float:
        """Perform basic arithmetic operations."""
        if operation == "add":
            return a + b
        elif operation == "subtract":
            return a - b
        elif operation == "multiply":
            return a * b
        elif operation == "divide":
            return a / b if b != 0 else float('inf')
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    @remote_server.resource("data://numbers/{count}")
    def generate_numbers(count: int) -> str:
        """Generate a list of numbers."""
        return ", ".join(str(i) for i in range(1, count + 1))
    
    @remote_server.prompt
    def greeting(name: str, style: str = "formal") -> str:
        """Generate a greeting message."""
        if style == "formal":
            return f"Good day, {name}. How may I assist you today?"
        elif style == "casual":
            return f"Hey {name}! What's up?"
        else:
            return f"Hello, {name}!"
    
    print(f"   Remote server '{remote_server.name}' created with tools, resources, and prompts.")
    
    # Create a proxy server (in this case, using in-memory connection)
    print("\n2. Creating proxy server...")
    proxy_server = FastMCP.as_proxy(remote_server, name="CalculatorProxy")
    print(f"   Proxy server '{proxy_server.name}' created.")
    
    # Use the proxy server
    print("\n3. Testing proxy functionality...")
    async with Client(proxy_server) as client:
        # Test tools
        print("   Testing tools...")
        tools = await client.list_tools()
        print(f"   Found {len(tools)} tools: {[t.name for t in tools]}")
        
        result = await client.call_tool("calculate", {
            "operation": "add", 
            "a": 10, 
            "b": 5
        })
        print(f"   Tool result: 10 + 5 = {result[0].text}")
        
        # Test resources
        print("   Testing resources...")
        resources = await client.list_resources()
        print(f"   Found {len(resources)} resources: {[str(r.uri) for r in resources]}")
        
        resource_content = await client.read_resource("data://numbers/5")
        print(f"   Resource content: {resource_content[0].text}")
        
        # Test prompts
        print("   Testing prompts...")
        prompts = await client.list_prompts()
        print(f"   Found {len(prompts)} prompts: {[p.name for p in prompts]}")
        
        prompt_result = await client.get_prompt("greeting", {
            "name": "Alice", 
            "style": "casual"
        })
        print(f"   Prompt result: {prompt_result.messages[0].content.text}")
    
    print("\n✅ Programmatic usage example completed successfully!")


def example_command_line_usage():
    """Example of command-line usage."""
    print("\n=== Command Line Usage Examples ===")
    
    examples = [
        {
            "description": "Basic stdio proxy (most common)",
            "command": "python mcp_proxy_server.py http://localhost:8000/mcp"
        },
        {
            "description": "HTTP proxy server on port 8001",
            "command": "python mcp_proxy_server.py http://localhost:8000/mcp --transport http --port 8001"
        },
        {
            "description": "SSE proxy server with custom name",
            "command": "python mcp_proxy_server.py http://localhost:8000/sse --transport sse --port 8002 --name 'MySSEProxy'"
        },
        {
            "description": "Force SSE transport for remote connection",
            "command": "python mcp_proxy_server.py http://localhost:8000/mcp --transport-type sse"
        },
        {
            "description": "Proxy a remote MCP server running on different host",
            "command": "python mcp_proxy_server.py https://api.example.com/mcp --name 'ExternalProxy'"
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['description']}:")
        print(f"   {example['command']}")
    
    print("\n📝 Usage Notes:")
    print("   - Default transport is 'stdio' (works with MCP clients like Claude Desktop)")
    print("   - Use 'http' or 'sse' transport to run as a web server")
    print("   - The proxy automatically detects the remote server's transport type")
    print("   - Use --transport-type to force a specific transport for remote connections")


async def main():
    """Run all examples."""
    print("🚀 MCP Proxy Server Examples")
    print("=" * 50)
    
    # Run programmatic example
    await example_programmatic_usage()
    
    # Show command-line examples
    example_command_line_usage()
    
    print("\n" + "=" * 50)
    print("🎉 All examples completed!")
    print("\nTo run the proxy server, use:")
    print("   python mcp_proxy_server.py <mcp_url> [options]")
    print("\nFor help:")
    print("   python mcp_proxy_server.py --help")


if __name__ == "__main__":
    asyncio.run(main())