# MCP Proxy Server

A standalone FastMCP server that acts as a proxy to any remote MCP-compliant server. Given an MCP URL, it connects to the remote server and exposes all its capabilities (tools, resources, prompts) through the proxy server.

## Features

- **Universal Proxy**: Connect to any MCP server via HTTP, HTTPS, or SSE
- **Full MCP Support**: Proxies all MCP capabilities (tools, resources, resource templates, prompts)
- **Multiple Transports**: Run the proxy via stdio, HTTP, or SSE
- **Auto-Detection**: Automatically detects the remote server's transport type
- **Error Handling**: Graceful error handling and connection management
- **Session Management**: Proper session isolation and cleanup

## Installation

The proxy server is built using FastMCP 2.0. Ensure you have the FastMCP library installed:

```bash
pip install fastmcp
```

## Usage

### Command Line Interface

```bash
python mcp_proxy_server.py <mcp_url> [options]
```

#### Options

- `mcp_url`: URL of the remote MCP server to proxy (required)
- `--name`: Name for the proxy server (default: "MCPProxy")
- `--port`: Port to run the proxy server on (for HTTP/SSE transports)
- `--transport`: Transport type for the proxy server (`stdio`, `http`, `sse`) (default: `stdio`)
- `--transport-type`: Force specific transport type for connecting to remote server (`sse`, `http`)

### Examples

#### 1. Basic stdio proxy (most common)
```bash
python mcp_proxy_server.py http://localhost:8000/mcp
```
This creates a stdio-based proxy that can be used with MCP clients like Claude Desktop.

#### 2. HTTP proxy server
```bash
python mcp_proxy_server.py http://localhost:8000/mcp --transport http --port 8001
```
Runs the proxy as an HTTP server on port 8001.

#### 3. SSE proxy server with custom name
```bash
python mcp_proxy_server.py http://localhost:8000/sse --transport sse --port 8002 --name "MySSEProxy"
```
Runs the proxy as an SSE server with a custom name.

#### 4. Force transport type for remote connection
```bash
python mcp_proxy_server.py http://localhost:8000/mcp --transport-type sse
```
Forces the proxy to use SSE when connecting to the remote server.

#### 5. Proxy external MCP server
```bash
python mcp_proxy_server.py https://api.example.com/mcp --name "ExternalProxy"
```
Proxies a remote MCP server running on a different host.

### Programmatic Usage

You can also use the proxy server programmatically:

```python
import asyncio
from fastmcp.client import Client
from mcp_proxy_server import create_proxy_server

async def main():
    # Create proxy server
    proxy_server = await create_proxy_server(
        mcp_url="http://localhost:8000/mcp",
        proxy_name="MyProxy"
    )
    
    # Use the proxy
    async with Client(proxy_server) as client:
        tools = await client.list_tools()
        print(f"Available tools: {[t.name for t in tools]}")
        
        # Call a tool
        result = await client.call_tool("some_tool", {"param": "value"})
        print(f"Result: {result}")

asyncio.run(main())
```

## Architecture

The MCP Proxy Server consists of several key components:

1. **Client Factory**: Creates client instances to connect to the remote MCP server
2. **FastMCPProxy**: The main proxy server that uses specialized managers
3. **Proxy Managers**: Handle tools, resources, and prompts from the remote server
4. **Transport Layer**: Supports multiple transport types for both client and server connections

### How It Works

1. **Connection**: The proxy creates a client connection to the remote MCP server
2. **Discovery**: It discovers all available tools, resources, and prompts from the remote server
3. **Proxying**: When a client connects to the proxy, it forwards all requests to the remote server
4. **Response**: Results from the remote server are returned to the client through the proxy

## Transport Types

### For Remote Server Connection
- **Auto-detection**: Automatically detects based on URL
- **HTTP**: Standard HTTP requests (`--transport-type http`)
- **SSE**: Server-Sent Events (`--transport-type sse`)

### For Proxy Server
- **stdio**: Standard input/output (default, works with Claude Desktop)
- **http**: HTTP server (`--transport http --port <port>`)
- **sse**: Server-Sent Events server (`--transport sse --port <port>`)

## Error Handling

The proxy server includes comprehensive error handling:

- **Connection Errors**: Graceful handling of remote server connection failures
- **Tool Errors**: Proper forwarding of tool execution errors
- **Resource Errors**: Handling of missing or inaccessible resources
- **Timeout Handling**: Configurable timeouts for remote server connections

## Testing

Run the test suite to verify functionality:

```bash
python test_mcp_proxy_server.py
```

The tests cover:
- Client factory creation
- Proxy server setup
- Tool, resource, and prompt proxying
- Error handling
- Multiple tool types

## Example Scenarios

### Scenario 1: Local Development
You have an MCP server running locally and want to test it with different clients:

```bash
# Start your MCP server on port 8000
python your_mcp_server.py --port 8000

# Start the proxy via stdio
python mcp_proxy_server.py http://localhost:8000/mcp

# Now you can connect Claude Desktop or other MCP clients to the proxy
```

### Scenario 2: Remote Server Access
You want to access a remote MCP server through a local proxy:

```bash
# Proxy a remote server
python mcp_proxy_server.py https://api.example.com/mcp --name "RemoteProxy"
```

### Scenario 3: Protocol Translation
You have an HTTP MCP server but need SSE access:

```bash
# Run proxy as SSE server, connecting to HTTP remote server
python mcp_proxy_server.py http://localhost:8000/mcp --transport sse --port 8001
```

## Limitations

- The proxy adds a small latency overhead due to the additional network hop
- Session state is not shared between proxy instances
- Some advanced MCP features may require specific transport types

## Contributing

To contribute to the MCP Proxy Server:

1. Follow the FastMCP development guidelines
2. Run the validation commands: `uv sync && uv run pre-commit run --all-files && uv run pytest`
3. Add tests for new features
4. Update documentation as needed

## License

This project follows the same license as FastMCP.