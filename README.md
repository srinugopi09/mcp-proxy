# MCP Proxy Server with Registry

A standalone proxy server implementation for the Model Context Protocol (MCP) built with FastMCP 2.0, featuring server discovery and registry capabilities.

## Overview

This repository contains a complete MCP proxy server that can connect to any remote MCP server via URL and expose all its capabilities (tools, resources, prompts) through the proxy server. It includes a built-in registry system for server discovery and management.

## Features

- **Universal Proxy**: Connect to any MCP server via HTTP, HTTPS, or SSE
- **Server Registry**: Register, discover, and manage MCP servers
- **REST API**: FastAPI-based API for server management
- **Health Monitoring**: Connectivity testing and status tracking
- **Full MCP Support**: Proxies all MCP capabilities (tools, resources, resource templates, prompts)
- **Multiple Transports**: Run the proxy via stdio, HTTP, or SSE
- **Auto-Detection**: Automatically detects the remote server's transport type
- **Error Handling**: Graceful error handling and connection management
- **Session Management**: Proper session isolation and cleanup

## Quick Start

### Installation

#### Using UV (Recommended)
```bash
# Install UV if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone -b feature/registry-increment-1 https://github.com/srinugopi09/mcp-proxy.git
cd mcp-proxy

# Install dependencies with UV
uv sync

# Activate the virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

#### Using pip (Alternative)
```bash
# Clone the repository
git clone -b feature/registry-increment-1 https://github.com/srinugopi09/mcp-proxy.git
cd mcp-proxy

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

#### Direct URL Connection (Original Mode)
```bash
# Using UV (recommended)
uv run python mcp_proxy_server.py http://localhost:8000/mcp

# Proxy via HTTP on port 8001
uv run python mcp_proxy_server.py http://localhost:8000/mcp --transport http --port 8001

# Proxy via SSE with custom name
uv run python mcp_proxy_server.py http://localhost:8000/sse --transport sse --port 8002 --name "MyProxy"

# Using the installed script
uv run mcp-proxy http://localhost:8000/mcp
```

#### Registry-Based Connection (New Mode)
```bash
# Start registry API only
uv run python mcp_proxy_server.py --enable-registry --api-port 8080

# Connect to registered server by ID
uv run python mcp_proxy_server.py --server-id weather-service-123 --transport http --port 8001

# Start registry API and proxy a registered server
uv run python mcp_proxy_server.py --enable-registry --server-id weather-service --api-port 8080

# Using the installed script
uv run mcp-proxy --enable-registry --api-port 8080
```

## Registry API

The registry provides a REST API for managing MCP servers:

### Server Management
```bash
# Register a new server
curl -X POST http://localhost:8080/api/servers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Weather Service",
    "url": "http://localhost:8001/mcp",
    "description": "Provides weather information",
    "tags": ["weather", "external-api"],
    "transport": "http"
  }'

# List all servers
curl http://localhost:8080/api/servers

# Get server details
curl http://localhost:8080/api/servers/{server-id}

# Update server
curl -X PUT http://localhost:8080/api/servers/{server-id} \
  -H "Content-Type: application/json" \
  -d '{"description": "Updated description"}'

# Delete server
curl -X DELETE http://localhost:8080/api/servers/{server-id}

# Update server status
curl -X PATCH http://localhost:8080/api/servers/{server-id}/status \
  -H "Content-Type: application/json" \
  -d '{"status": "healthy"}'
```

### API Documentation
When the registry is running, visit:
- **Swagger UI**: `http://localhost:8080/api/docs`
- **ReDoc**: `http://localhost:8080/api/redoc`

## Files

- **`mcp_proxy_server.py`** - Main proxy server with registry integration
- **`registry/`** - Registry system components
  - **`models.py`** - Pydantic models for API
  - **`database.py`** - SQLite database operations
  - **`api.py`** - FastAPI endpoints
- **`test_mcp_proxy_server.py`** - Original proxy tests
- **`test_registry.py`** - Registry functionality tests
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

### Using UV (Recommended)
```bash
# Install test dependencies
uv sync --extra test

# Run the proxy test suite
uv run python test_mcp_proxy_server.py

# Run the registry test suite
uv run python test_registry.py

# Run the fix verification
uv run python test_fix.py

# Run with pytest (if available)
uv run pytest test_registry.py -v
```

### Using pip (Alternative)
```bash
# Install test dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx

# Run the test suites
python test_mcp_proxy_server.py
python test_registry.py
python test_fix.py
```

## Requirements

- Python ≥ 3.10
- UV (recommended) or pip for dependency management

### Dependencies (managed automatically)
- FastMCP 2.0
- FastAPI (for registry functionality)
- Uvicorn (for API server)
- Pydantic (for data validation)

## Database

The registry uses SQLite for data storage. By default, the database is created as `./mcp_registry.db`. You can specify a custom path using the `--db-path` argument or `MCP_REGISTRY_DB` environment variable.

## License

This project follows the same license as FastMCP.