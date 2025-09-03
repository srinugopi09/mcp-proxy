# MCP Proxy Server

A standalone proxy server implementation for the Model Context Protocol (MCP) built with FastMCP 2.0.

## Overview

This repository contains a complete MCP proxy server that can connect to any remote MCP server via URL and expose all its capabilities (tools, resources, prompts) through the proxy server.

## Features

- **Universal Proxy**: Connect to any MCP server via HTTP, HTTPS, or SSE
- **Full MCP Support**: Proxies all MCP capabilities (tools, resources, resource templates, prompts)
- **Multiple Transports**: Run the proxy via stdio, HTTP, or SSE
- **Auto-Detection**: Automatically detects the remote server's transport type
- **Error Handling**: Graceful error handling and connection management
- **Session Management**: Proper session isolation and cleanup

## Quick Start

### Installation

```bash
# Install FastMCP
pip install fastmcp

# Clone this repository
git clone https://github.com/srinugopi09/mcp-proxy.git
cd mcp-proxy
```

### Basic Usage

```bash
# Proxy via stdio (works with Claude Desktop)
python mcp_proxy_server.py http://localhost:8000/mcp

# Proxy via HTTP on port 8001
python mcp_proxy_server.py http://localhost:8000/mcp --transport http --port 8001

# Proxy via SSE with custom name
python mcp_proxy_server.py http://localhost:8000/sse --transport sse --port 8002 --name "MyProxy"
```

## Files

- **`mcp_proxy_server.py`** - Main proxy server implementation
- **`test_mcp_proxy_server.py`** - Comprehensive test suite
- **`example_usage.py`** - Usage examples and demonstrations
- **`MCP_PROXY_README.md`** - Detailed documentation
- **`test_fix.py`** - Fix verification script

## Documentation

See [MCP_PROXY_README.md](MCP_PROXY_README.md) for complete documentation including:
- Detailed usage instructions
- Command-line options
- Programmatic usage examples
- Architecture explanation
- Transport types and configuration

## Testing

Run the test suite:

```bash
python test_mcp_proxy_server.py
```

Run the fix verification:

```bash
python test_fix.py
```

## Requirements

- Python ≥ 3.10
- FastMCP 2.0

## License

This project follows the same license as FastMCP.